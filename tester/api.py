"""Team 17's tester (the course's cross-team testing interface), served under
/tester: POST /tester/test/setup, POST /tester/test/run, GET /tester/test/report.

Targets are limited to this service and the approved pod systems
(tester.runner.allowed_target). These routes run outside the request transaction
(cra_service.middleware), so a session's state is visible to other requests while
its suite runs. One run at a time, and recovery of runs cut off by a restart:
tester.sessions.
"""

import logging
import uuid
from urllib.parse import urlsplit

from ninja import Router
from ninja.responses import Status
from pydantic import Field

from core import clock
from cra_service.errors import BadRequest, field_error, interface_problem
from cra_service.validation import RequestSchema, parse_body
from tester import runner, sessions
from tester.models import TesterSession

logger = logging.getLogger(__name__)

router = Router(tags=["tester"])

SOURCES = {"tester", "system", "communication", "unknown"}

ANOTHER_RUN = "Another test run is in progress; try again when it ends"


class SetupIn(RequestSchema):
    target_url: str = Field(min_length=1, max_length=2000)


class RunIn(RequestSchema):
    session_id: str = Field(min_length=1, max_length=200)


def _invalid(errors):
    return interface_problem(400, "Invalid request", "tester", errors)


def _base_url(value: str) -> str | None:
    """The target's base URL without a trailing slash, or None if it isn't a plain
    HTTP(S) base URL (no query, fragment, or credentials)."""
    parts = urlsplit(value)
    if (
        parts.scheme not in ("http", "https")
        or not parts.hostname
        or parts.query
        or parts.fragment
        or parts.username
        or parts.password
    ):
        return None
    return value.rstrip("/")


@router.post("/setup", response={201: dict}, operation_id="testerSetup")
def setup(request):
    try:
        payload = parse_body(request, SetupIn)
    except BadRequest as error:
        return _invalid(error.errors)
    target = _base_url(payload.target_url)
    if target is None:
        return _invalid([field_error("target_url", "must be an HTTP(S) base URL")])
    if not runner.allowed_target(target):
        return _invalid([field_error("target_url", "is not an approved pod system")])
    # A target's setup may reset it, so not while a run is using the shared database.
    if sessions.run_in_progress():
        return interface_problem(409, ANOTHER_RUN, "tester")
    session_id = f"run-{uuid.uuid4()}"
    try:
        status, body = runner.call(
            target,
            "POST",
            "/test/setup",
            {"session_id": session_id, "setup": {}},
            timeout=runner.SETUP_TIMEOUT,
        )
    except runner.CommunicationError as error:
        return interface_problem(500, f"System setup failed: {error}", "communication")
    if status != 201:
        message = body.get("message") or body.get("detail") or body.get("title")
        source = body.get("source") if body.get("source") in SOURCES else "system"
        return interface_problem(
            status if 400 <= status < 600 else 500,
            str(message or f"System setup returned {status}"),
            source,
        )
    if body.get("session_id") != session_id:
        return interface_problem(500, "System setup did not return the session ID", "system")
    TesterSession.objects.create(session_id=session_id, target_url=target, created_at=clock.now())
    return Status(201, {"session_id": session_id})


@router.post("/run", response=dict, operation_id="testerRun")
def run(request):
    try:
        payload = parse_body(request, RunIn)
    except BadRequest as error:
        return _invalid(error.errors)
    claimed = sessions.claim(payload.session_id)
    if claimed == sessions.UNKNOWN:
        return interface_problem(404, "Unknown session", "tester")
    if claimed == sessions.USED:
        return interface_problem(409, "This session has already run", "tester")
    if claimed == sessions.BUSY:
        return interface_problem(409, ANOTHER_RUN, "tester")
    session = TesterSession.objects.get(pk=payload.session_id)
    heartbeat = sessions.Heartbeat(session.session_id)
    heartbeat.start()
    try:
        try:
            report, aborted = runner.run_suite(
                session.session_id, session.target_url, on_start=heartbeat.started
            )
        except Exception as error:
            logger.error("Tester session %s crashed: %s", session.session_id, type(error).__name__)
            aborted = "The tester failed while running the suite"
            report = runner.failed_report(session.session_id, session.target_url, aborted)
        # Before the session stops counting as running, so the cleanup can't reset a
        # target that the next run is already using. If its state can't be read, the
        # run is most likely still ours: clean up anyway.
        if not heartbeat.cancelled:
            try:
                sessions.fresh_connection()
                ours = sessions.still_running(session.session_id)
            except Exception as error:
                logger.error(
                    "Tester session %s: state unreadable: %s",
                    session.session_id,
                    type(error).__name__,
                )
                ours = True
            if ours:
                runner.clean_up_target(session.target_url, session.session_id)
    finally:
        heartbeat.stop()
    if heartbeat.cancelled:  # recovery stored a report while the suite was still going
        return interface_problem(500, sessions.CUT_OFF, "tester")
    try:
        sessions.fresh_connection()
        stored = sessions.finish(session.session_id, report)
    except Exception as error:
        # The session stays running until its heartbeat goes stale; recovery then
        # stores the outcomes the heartbeat saved.
        logger.error(
            "Tester session %s: report not stored: %s", session.session_id, type(error).__name__
        )
        return interface_problem(500, "The tester could not store its report", "tester")
    if not stored:
        return interface_problem(500, sessions.CUT_OFF, "tester")
    if aborted:
        return interface_problem(500, aborted, "tester")
    return report


@router.get("/report", response=dict, operation_id="testerReport")
def report(request):
    session_id = request.GET.get("session_id", "")
    if not session_id:
        return _invalid([field_error("session_id", "required")])
    session = TesterSession.objects.filter(pk=session_id).first()
    if session is None:
        return interface_problem(404, "Unknown session", "tester")
    if session.state == "running":
        sessions.recover_stale()
        session.refresh_from_db()
    if session.state != "finished":
        return interface_problem(409, "The suite has not finished", "tester")
    return session.report
