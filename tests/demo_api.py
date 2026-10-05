"""A throwaway API, mounted only in tests (tests/urls.py), that exercises the
platform the way ticket routes will: lookup (404), X-Actor and body (400),
state (409), rules (422)."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from django.http import HttpResponse
from ninja import Schema
from pydantic import StringConstraints

from core import clock
from cra_service.api import ServiceAPI
from cra_service.errors import Conflict, NotFound, RuleViolation, field_error
from cra_service.timestamps import Timestamp
from cra_service.validation import RequestSchema, parse_body, require_actor

demo = ServiceAPI(urls_namespace="demo", docs_url=None, openapi_url=None)

THINGS = {"open", "locked"}
ShortText = Annotated[str, StringConstraints(min_length=1, max_length=200)]


class Kind(StrEnum):
    early_warning = "early_warning"
    notification = "notification"


class Product(RequestSchema):
    manufacturer: ShortText
    affected_versions: list[ShortText] = []


class ThingUpdate(RequestSchema):
    title: ShortText
    kind: Kind | None = None
    when: Timestamp | None = None
    product: Product | None = None


class ThingOut(Schema):
    id: str
    actor: str
    title: str
    when: Timestamp | None


@demo.patch("/things/{id}", response=ThingOut)
def update_thing(request, id: str):
    if id not in THINGS:
        raise NotFound()
    actor = require_actor(request)
    payload = parse_body(request, ThingUpdate)
    if id == "locked":
        raise Conflict("The thing is locked.")
    if payload.title == "breaks-rule":
        raise RuleViolation([field_error("title", "breaks a rule")])
    return {"id": id, "actor": actor, "title": payload.title, "when": payload.when}


class Note(RequestSchema):
    text: ShortText | None = None


@demo.post("/things/{id}/notes")
def add_note(request, id: str):
    if id not in THINGS:
        raise NotFound()
    require_actor(request)
    payload = parse_body(request, Note, required=False)
    return {"text": payload.text}


@demo.post("/typed", response=ThingOut)
def typed(request, payload: ThingUpdate):
    return {"id": "typed", "actor": "-", "title": payload.title, "when": payload.when}


@demo.get("/kinds/{kind}")
def get_kind(request, kind: Kind):
    return {"kind": kind.value}


@demo.get("/search")
def search(request, kind: Kind | None = None):
    return {"kind": kind.value if kind else None}


@demo.post("/conflict-after-write")
def conflict_after_write(request):
    clock.fix(datetime(2030, 1, 1, tzinfo=UTC))
    raise Conflict()


@demo.post("/crash-after-write")
def crash_after_write(request):
    clock.fix(datetime(2030, 1, 1, tzinfo=UTC))
    # Like a database or pydantic error, the message quotes request data.
    raise RuntimeError(f"bad input: {request.body.decode()}")


def django_crash(request) -> HttpResponse:
    """A plain Django view (not ninja) that writes, then fails."""
    clock.fix(datetime(2030, 1, 1, tzinfo=UTC))
    raise RuntimeError(f"bad input: {request.body.decode()}")
