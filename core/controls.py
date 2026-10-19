"""Test controls (REQ-16). Must stay enabled on evaluation deployments.

These routes do not take X-Actor: they change test state, not ticket data.
"""

from django.apps import apps
from django.core.management.color import no_style
from django.db import connection
from ninja import Router, Schema
from ninja.responses import Status
from pydantic import Field

from core import clock
from core.models import FixedClock, SystemSession
from cra_service.errors import BadRequest, field_error, interface_problem
from cra_service.timestamps import Timestamp
from cra_service.validation import RequestSchema, parse_body

router = Router(tags=["testing"])

# Every model in these apps is application data and is cleared by reset, except
# the fixed clock: openapi.yaml says reset deletes tickets, reports, and audit
# entries, and says nothing about releasing the clock.
RESET_APPS = ("core",)
KEPT_ON_RESET = {FixedClock, SystemSession}

# The course's cross-team testing interface: a tester prepares this system with
# POST /test/setup, then reads code coverage from GET /test/report. Setup records the
# session only; POST /test/reset stays the pod's way to clear data.
CODE_COVERAGE_BASIS = "Source lines; the deployed service is not instrumented for code coverage"


class ClockIn(RequestSchema):
    now: Timestamp


class ClockOut(Schema):
    now: Timestamp


class SetupIn(RequestSchema):
    session_id: str = Field(min_length=1, max_length=200)
    setup: dict = Field(default_factory=dict)


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


@router.post("/setup", response={201: dict}, operation_id="setupSession")
def setup_session(request):
    try:
        payload = parse_body(request, SetupIn)
    except BadRequest as error:
        return interface_problem(400, "Invalid setup request", "system", error.errors)
    if SystemSession.objects.filter(pk=payload.session_id).exists():
        return interface_problem(409, "Session ID already exists", "system")
    SystemSession.objects.create(session_id=payload.session_id, created_at=clock.now())
    return Status(201, {"session_id": payload.session_id})


@router.get("/report", response=dict, operation_id="getSessionReport")
def session_report(request):
    session_id = request.GET.get("session_id", "")
    if not session_id:
        return interface_problem(
            400, "session_id is required", "system", [field_error("session_id", "required")]
        )
    if not SystemSession.objects.filter(pk=session_id).exists():
        return interface_problem(404, "Unknown session", "system")
    return {
        "session_id": session_id,
        "coverage": {"code": {"covered": None, "total": None, "basis": CODE_COVERAGE_BASIS}},
    }
