"""Test controls (REQ-16). Must stay enabled on evaluation deployments.

These routes do not take X-Actor: they change test state, not ticket data.
"""

from django.apps import apps
from django.core.management.color import no_style
from django.db import connection
from ninja import Router, Schema
from ninja.responses import Status

from core import clock
from core.models import FixedClock
from cra_service.timestamps import Timestamp
from cra_service.validation import RequestSchema

router = Router(tags=["testing"])

# Every model in these apps is application data and is cleared by reset, except
# the fixed clock: openapi.yaml says reset deletes tickets, reports, and audit
# entries, and says nothing about releasing the clock.
RESET_APPS = ("core",)
KEPT_ON_RESET = {FixedClock}


class ClockIn(RequestSchema):
    now: Timestamp


class ClockOut(Schema):
    now: Timestamp


def reset_models() -> list:
    return [
        model
        for label in RESET_APPS
        for model in apps.get_app_config(label).get_models()
        if model not in KEPT_ON_RESET
    ]


@router.post("/reset", response={204: None}, operation_id="resetService")
def reset_service(request):
    tables = [model._meta.db_table for model in reset_models()]
    # TRUNCATE ... CASCADE on Postgres, so foreign keys between tables never
    # dictate the order. Runs inside the request transaction.
    statements = connection.ops.sql_flush(
        no_style(), tables, reset_sequences=False, allow_cascade=True
    )
    with connection.cursor() as cursor:
        for sql in statements:
            cursor.execute(sql)
    return Status(204, None)


@router.get("/clock", response=ClockOut, operation_id="getClock")
def get_clock(request):
    return {"now": clock.now()}


@router.put("/clock", response=ClockOut, operation_id="setClock")
def set_clock(request, payload: ClockIn):
    return {"now": clock.fix(payload.now)}


@router.delete("/clock", response={204: None}, operation_id="releaseClock")
def release_clock(request):
    clock.release()
    return Status(204, None)
