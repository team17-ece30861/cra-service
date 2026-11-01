"""Console report pages (4.U3): the Report Draft page, Record Submission and Close Ticket. They
show what the API returns, make exactly one change per POST as the signed-in person, and keep
reporter details to the ticket page."""

from copy import deepcopy

import pytest
from django.contrib.auth.models import User
from django.test import Client

from acceptance.draft_cases import FIELDS
from console import present_reports
from core.domain.closure import close_ticket
from core.models import AuditEntry, ReportSubmission, Ticket
from cra_service.errors import Conflict
from cra_service.validation import ACTOR_HEADER

pytestmark = pytest.mark.django_db

PASSWORD = "correct horse battery"
REPORTER_NAME = "Zelda Unique-Reporter-7731"
NOW = "2026-10-29T14:00:00Z"
AWARE = "2026-10-29T10:40:00Z"  # the early warning is due 24 h later: 2026-10-30T10:40:00Z


@pytest.fixture
def api(authed):
    """The API with the bearer token, and the clock fixed at NOW."""
    assert (
        authed.put("/test/clock", {"now": NOW}, content_type="application/json").status_code == 200
    )
    yield authed
    authed.delete("/test/clock")


@pytest.fixture
def console():
    user = User.objects.create_user("m.okafor", password=PASSWORD)
    client = Client()
    client.force_login(user)
    return client


def _create(api, **fields):
    body = {
        "source": "external_researcher",
        "title": "Heap overflow in OTA update parser",
        "description": "A crafted manifest overflows the parser.",
        "product": {"manufacturer": "Nordvik", "name": "Lumen Gateway 4"},
        "reporter": {"name": REPORTER_NAME, "contact": "zelda@example.invalid"},
        **fields,
    }
    response = api.post(
        "/tickets", body, content_type="application/json", headers={ACTOR_HEADER: "intake"}
    )
    assert response.status_code == 201, response.content
    return response.json()["id"]


def _triage(api, ticket_id):
    response = api.post(
        f"/tickets/{ticket_id}/triage",
        {"decision": "actively_exploited", "reason": "Seen in the wild.", "aware_at": AWARE},
        content_type="application/json",
        headers={ACTOR_HEADER: "intake"},
    )
    assert response.status_code == 200, response.content


def _submit(api, ticket_id, kind):
    response = api.post(
        f"/tickets/{ticket_id}/reports/{kind}/submission",
        {},
        content_type="application/json",
        headers={ACTOR_HEADER: "intake"},
    )
    assert response.status_code == 200, response.content


def _missing_fields_ticket(api):
    """Reportable, but the early warning still needs affected versions and member states."""
    ticket_id = _create(api)
    _triage(api, ticket_id)
    return ticket_id


def _complete_ticket(api):
    """Reportable, with every field every report needs."""
    fields = deepcopy(FIELDS)
    fields["reporter"] = {"name": REPORTER_NAME, "contact": "zelda@example.invalid"}
    ticket_id = _create(api, **fields)
    _triage(api, ticket_id)
    return ticket_id


def _ready_to_close(api):
    ticket_id = _complete_ticket(api)
    for kind in ("early_warning", "notification", "final_report"):
        _submit(api, ticket_id, kind)
    return ticket_id


def _record(console, ticket_id, kind="early_warning", **data):
    return console.post(f"/console/tickets/{ticket_id}/reports/{kind}/record", data)


def _close(api, ticket_id):
    response = api.post(f"/tickets/{ticket_id}/close", headers={ACTOR_HEADER: "intake"})
    assert response.status_code == 200, response.content


# --- Signed out ---


@pytest.mark.parametrize(
    "path",
    [
        "/console/tickets/x/reports/early_warning",
        "/console/tickets/x/reports/early_warning/record",
        "/console/tickets/x/close",
    ],
)
@pytest.mark.parametrize("method", ["get", "post"])
def test_signed_out_people_go_to_sign_in(path, method):
    response = getattr(Client(), method)(path)
    assert response.status_code == 302
    assert response["Location"].startswith("/console/sign-in?next=")


# --- Report Draft page ---


def test_draft_shows_the_missing_fields_the_api_names(api, console):
    ticket_id = _missing_fields_ticket(api)
    page = console.get(f"/console/tickets/{ticket_id}/reports/early_warning")
    assert page.status_code == 200
    html = page.content.decode()
    assert "2 required fields are missing" in html
    assert html.count('<dt class="missing">') == 2
    assert "product.affected_versions" in html and "member_states" in html
    edit = f"/console/tickets/{ticket_id}/edit?focus="
    assert f'{edit}member_states"' in html
    assert f'{edit}product.affected_versions"' in html
    # Record is off until the API stops naming missing fields
    assert 'id="rp-record" disabled' in html
    assert "Due 2026-10-30 10:40:00 UTC" in html
    assert REPORTER_NAME not in html


def test_complete_draft_is_ready_with_its_content(api, console):
    ticket_id = _complete_ticket(api)
    html = console.get(f"/console/tickets/{ticket_id}/reports/notification").content.decode()
    assert "Ready to send" in html
    assert 'class="missing"' not in html
    assert "Authentication bypass" in html and "TLP:AMBER" in html
    assert f'href="/console/tickets/{ticket_id}/reports/notification/record"' in html
    assert "data-copy-report=" in html
    assert REPORTER_NAME not in html


def test_user_advisory_has_no_deadline_and_nothing_to_record(api, console):
    ticket_id = _complete_ticket(api)
    html = console.get(f"/console/tickets/{ticket_id}/reports/user_advisory").content.decode()
    assert "No deadline" in html and "For your users, not the authority" in html
    assert 'id="rp-record"' not in html
    record = console.get(f"/console/tickets/{ticket_id}/reports/user_advisory/record")
    assert record.status_code == 404


def test_a_ticket_that_never_became_reportable_has_no_draft(api, console):
    ticket_id = _create(api)
    page = console.get(f"/console/tickets/{ticket_id}/reports/early_warning")
    assert page.status_code == 200
    assert "There's no draft for this ticket" in page.content.decode()


@pytest.mark.parametrize(
    "path", ["/console/tickets/nope/reports/early_warning", "/console/tickets/{id}/reports/bogus"]
)
def test_unknown_tickets_and_report_types_are_not_found(api, console, path):
    ticket_id = _create(api)
    assert console.get(path.format(id=ticket_id)).status_code == 404


def test_a_failed_draft_read_shows_an_error_page(api, console, monkeypatch):
    from console import views_reports
    from console.api_calls import ApiResult

    ticket_id = _complete_ticket(api)
    real = views_reports.call_api

    def fake(request, method, path, **kwargs):
        if path.endswith("/reports/notification"):
            return ApiResult(503, {"title": "Service Unavailable", "status": 503})
        return real(request, method, path, **kwargs)

    monkeypatch.setattr(views_reports, "call_api", fake)
    response = console.get(f"/console/tickets/{ticket_id}/reports/notification")
    assert response.status_code == 503
    assert "This report couldn&#x27;t be loaded." in response.content.decode()


# --- Record Submission ---


def test_record_sheet_opens_over_the_draft_and_over_the_ticket(api, console):
    ticket_id = _complete_ticket(api)
    over_draft = console.get(f"/console/tickets/{ticket_id}/reports/early_warning/record")
    html = over_draft.content.decode()
    assert 'class="sheet-layer open"' in html and 'id="rs-form"' in html
    assert 'value="2026-10-29 14:00:00"' in html  # the service clock's now, not the browser's
    assert "rp-doc" in html
    assert REPORTER_NAME not in html
    over_ticket = console.get(
        f"/console/tickets/{ticket_id}/reports/early_warning/record?from=ticket"
    )
    html = over_ticket.content.decode()
    assert 'id="rs-form"' in html and "Audit trail" in html
    assert 'name="from" value="ticket"' in html


def test_recording_records_as_the_person_and_shows_a_toast(api, console):
    ticket_id = _complete_ticket(api)
    response = _record(
        console, ticket_id, submitted_at="2026-10-29 12:00:00", reference="CSIRT-DE-1051"
    )
    assert response.status_code == 302
    assert response["Location"] == f"/console/tickets/{ticket_id}"
    submission = ReportSubmission.objects.get(ticket_id=ticket_id)
    assert submission.report_type == "early_warning"
    assert submission.actor == "m.okafor"
    assert submission.reference == "CSIRT-DE-1051"
    assert submission.submitted_at.isoformat() == "2026-10-29T12:00:00+00:00"
    entry = AuditEntry.objects.get(ticket_id=ticket_id, action="report_submitted")
    assert entry.actor == "m.okafor"
    landed = console.get(response["Location"]).content.decode()
    assert 'data-flash-title="Early warning recorded"' in landed
    assert "Submitted on time. The report is locked as it read now." in landed
    # The toast shows once
    assert "data-flash-title" not in console.get(response["Location"]).content.decode()
    # The draft is now the locked copy
    html = console.get(f"/console/tickets/{ticket_id}/reports/early_warning").content.decode()
    assert "This is the locked copy that was recorded" in html
    assert "Submitted 2026-10-29 12:00:00 UTC · CSIRT-DE-1051" in html
    assert 'id="rp-record"' not in html


def test_an_empty_time_means_now(api, console):
    ticket_id = _complete_ticket(api)
    assert _record(console, ticket_id, submitted_at="", reference="").status_code == 302
    submission = ReportSubmission.objects.get(ticket_id=ticket_id)
    assert submission.submitted_at.isoformat() == "2026-10-29T14:00:00+00:00"
    assert submission.reference is None


def test_a_time_before_awareness_shows_the_error_and_records_nothing(api, console):
    ticket_id = _complete_ticket(api)
    response = _record(console, ticket_id, submitted_at="2026-10-29 09:00:00", reference="R-1")
    assert response.status_code == 422
    html = response.content.decode()
    assert (
        "Enter a time between when your team became aware (2026-10-29 10:40:00 UTC) and now."
        in html
    )
    assert 'value="2026-10-29 09:00:00"' in html and 'value="R-1"' in html
    assert 'class="sheet-layer open"' in html
    assert not ReportSubmission.objects.filter(ticket_id=ticket_id).exists()
    assert not AuditEntry.objects.filter(ticket_id=ticket_id, action="report_submitted").exists()


def test_a_badly_formed_time_shows_the_format(api, console):
    ticket_id = _complete_ticket(api)
    response = _record(console, ticket_id, submitted_at="yesterday")
    assert response.status_code == 400
    assert "Use the format 2026-10-29 14:00:00." in response.content.decode()
    assert not ReportSubmission.objects.exists()


def test_missing_fields_are_named_and_nothing_is_recorded(api, console):
    ticket_id = _missing_fields_ticket(api)
    response = _record(console, ticket_id, submitted_at="2026-10-29 12:00:00")
    assert response.status_code == 422
    html = response.content.decode()
    assert "2 required fields are missing: affected versions, member states." in html
    assert f"/console/tickets/{ticket_id}/edit?focus=product.affected_versions" in html
    assert not ReportSubmission.objects.exists()


def test_a_conflict_is_one_message_over_the_ticket(api, console):
    ticket_id = _complete_ticket(api)
    response = _record(console, ticket_id, "notification", **{"from": "ticket"})
    assert response.status_code == 409
    html = response.content.decode()
    assert "The previous report must be submitted first." in html
    assert "Audit trail" in html  # still over the ticket page it was opened from
    assert not ReportSubmission.objects.exists()


# --- Close Ticket ---


def test_close_not_ready_lists_what_is_left_and_does_not_close(api, console):
    ticket_id = _complete_ticket(api)
    _submit(api, ticket_id, "early_warning")
    page = console.get(f"/console/tickets/{ticket_id}/close")
    html = page.content.decode()
    assert page.status_code == 200
    assert "Not ready to close" in html and "Still to record:" in html
    dialog = html[html.index('data-sheet="close"') :]
    assert "<span>Notification</span>" in dialog and "<span>Final report</span>" in dialog
    assert "<span>Early warning</span>" not in dialog
    assert 'id="cl-go"' not in html
    response = console.post(f"/console/tickets/{ticket_id}/close")
    assert response.status_code == 409
    assert "All three reports must be submitted before closing the ticket." in (
        response.content.decode()
    )
    assert Ticket.objects.get(pk=ticket_id).state == "reportable"
    assert not AuditEntry.objects.filter(ticket_id=ticket_id, action="closed").exists()


def test_close_ready_closes_as_the_person(api, console):
    ticket_id = _ready_to_close(api)
    html = console.get(f"/console/tickets/{ticket_id}/close").content.decode()
    assert "Close this ticket?" in html and 'id="cl-go"' in html
    response = console.post(f"/console/tickets/{ticket_id}/close")
    assert response.status_code == 302
    assert response["Location"] == f"/console/tickets/{ticket_id}"
    ticket = Ticket.objects.get(pk=ticket_id)
    assert (ticket.state, ticket.resolution) == ("closed", "resolved")
    assert AuditEntry.objects.get(ticket_id=ticket_id, action="closed").actor == "m.okafor"
    landed = console.get(response["Location"]).content.decode()
    assert 'data-flash-title="Ticket closed"' in landed
    # A closed ticket no longer offers Close Ticket
    assert "Close Ticket…" not in landed


def test_close_unknown_ticket_is_not_found(console):
    assert console.get("/console/tickets/nope/close").status_code == 404
    assert console.post("/console/tickets/nope/close").status_code == 404


# --- The ticket page and list open the real flows ---


def test_ticket_page_links_to_drafts_record_and_close(api, console):
    ticket_id = _complete_ticket(api)
    html = console.get(f"/console/tickets/{ticket_id}").content.decode()
    assert f'href="/console/tickets/{ticket_id}/reports/early_warning"' in html
    assert f'href="/console/tickets/{ticket_id}/reports/early_warning/record?from=ticket"' in html
    assert f'data-sheet-open="/console/tickets/{ticket_id}/close"' in html
    assert 'data-sheet="close"' in html  # ready to open in place
    assert 'data-soon="View Draft"' not in html and 'data-soon="Close Ticket"' not in html
    listing = console.get("/console/").content.decode()
    assert f"/console/tickets/{ticket_id}/reports/early_warning/record?from=ticket" in listing


# --- CSRF ---


def test_changes_need_the_csrf_token(api):
    ticket_id = _ready_to_close(api)
    other = _complete_ticket(api)
    client = Client(enforce_csrf_checks=True)
    client.force_login(User.objects.create_user("m.okafor", password=PASSWORD))
    assert client.post(f"/console/tickets/{other}/reports/early_warning/record").status_code == 403
    assert client.post(f"/console/tickets/{ticket_id}/close").status_code == 403
    assert not ReportSubmission.objects.filter(ticket_id=other).exists()
    assert Ticket.objects.get(pk=ticket_id).state == "reportable"


# --- Presentation helpers ---


@pytest.mark.parametrize(
    ("typed", "sent"),
    [
        ("2026-10-29 14:00:00", "2026-10-29T14:00:00Z"),
        ("2026-10-29 14:00", "2026-10-29T14:00:00Z"),
        (" 2026-10-29T14:00:05Z ", "2026-10-29T14:00:05Z"),
        ("2026-10-29 14:00:00 UTC", "2026-10-29T14:00:00Z"),
        ("2026-10-29T14:00:00+02:00", "2026-10-29T14:00:00+02:00"),  # the API decides
        ("yesterday", "yesterday"),
    ],
)
def test_typed_times_go_to_the_api_in_its_form(typed, sent):
    assert present_reports.api_time(typed) == sent


# --- Review follow-ups (PR #94) ---


def test_report_tabs_have_a_name_at_every_width(api, console):
    ticket_id = _complete_ticket(api)
    html = console.get(f"/console/tickets/{ticket_id}/reports/early_warning").content.decode()
    tabs = html[html.index('id="rp-tabs"') : html.index('<span class="ind"')]
    for title in ("Early Warning", "Notification", "Final Report", "User Advisory"):
        assert f'aria-label="{title}"' in tabs
    assert "aria-hidden" not in tabs


def test_the_page_script_learns_where_a_change_landed_from_a_header(api, console):
    ticket_id = _ready_to_close(api)
    response = console.post(f"/console/tickets/{ticket_id}/close", headers={"X-Ledger-Sheet": "1"})
    assert response.status_code == 204
    assert response["X-Ledger-Done"] == f"/console/tickets/{ticket_id}"
    assert Ticket.objects.get(pk=ticket_id).state == "closed"
    landed = console.get(f"/console/tickets/{ticket_id}").content.decode()
    assert 'data-flash-title="Ticket closed"' in landed
    other = _complete_ticket(api)
    response = console.post(
        f"/console/tickets/{other}/reports/early_warning/record",
        {"submitted_at": "2026-10-29 12:00:00"},
        headers={"X-Ledger-Sheet": "1"},
    )
    assert response.status_code == 204
    assert response["X-Ledger-Done"] == f"/console/tickets/{other}"


def _obligations(statuses):
    return {
        kind: {"status": status}
        for kind, status in zip(
            ("early_warning", "notification", "final_report"), statuses, strict=True
        )
    }


@pytest.mark.parametrize(
    ("state", "statuses"),
    [
        ("reportable", ("submitted", "submitted", "submitted")),
        ("reportable", ("submitted_late", "submitted", "submitted_late")),
        ("reportable", ("submitted", "submitted", "pending")),
        ("reportable", ("submitted", "overdue", "awaiting_fix")),
        ("reportable", ("submitted", "submitted", "awaiting_fix")),
        ("reportable", ("pending", "pending", "awaiting_fix")),
        ("received", ("not_applicable", "not_applicable", "not_applicable")),
        ("closed", ("submitted", "submitted", "submitted")),
        ("closed", ("not_applicable", "not_applicable", "not_applicable")),
    ],
)
def test_close_dialog_agrees_with_the_closure_rule(state, statuses):
    """The dialog's ready / not ready mirrors core/domain/closure.py; a rule change breaks
    this test instead of silently hiding Close Ticket."""
    submitted = {
        kind
        for kind, ob in _obligations(statuses).items()
        if ob["status"] in ("submitted", "submitted_late")
    }
    try:
        close_ticket(state=state, submitted_reports=submitted)
        allowed = True
    except Conflict:
        allowed = False
    view = present_reports.close_view(
        {"state": state, "resolution": None, "obligations": _obligations(statuses)}
    )
    assert (view["variant"] == "ready") == allowed


def test_a_resolved_ticket_shows_its_locked_copies_and_nothing_to_record(api, console):
    ticket_id = _ready_to_close(api)
    _close(api, ticket_id)
    for kind in ("early_warning", "notification", "final_report"):
        html = console.get(f"/console/tickets/{ticket_id}/reports/{kind}").content.decode()
        assert "This is the locked copy that was recorded" in html
        assert 'id="rp-record"' not in html


def test_a_final_report_waiting_on_a_fix_cannot_be_recorded(api, console):
    fields = deepcopy(FIELDS)
    del fields["fix"]
    ticket_id = _create(api, **fields)
    _triage(api, ticket_id)
    html = console.get(f"/console/tickets/{ticket_id}/reports/final_report").content.decode()
    assert "Waiting on fix" in html
    assert "Due 14 days after a fix is available" in html
    assert 'id="rp-record" disabled' in html


def test_close_on_a_closed_ticket_says_so(api, console):
    ticket_id = _ready_to_close(api)
    _close(api, ticket_id)
    html = console.get(f"/console/tickets/{ticket_id}/close").content.decode()
    assert "Ticket closed" in html and "already closed as resolved." in html
    assert 'id="cl-go"' not in html


@pytest.mark.parametrize(
    ("typed", "status", "message"),
    [
        ("yesterday", 400, "Use the format 2026-10-29 14:00:00."),
        ("2026-10-29 09:00:00", 422, "Enter a time between when your team became aware"),
    ],
)
def test_errors_over_the_ticket_page_keep_the_ticket_page(api, console, typed, status, message):
    ticket_id = _complete_ticket(api)
    response = _record(console, ticket_id, submitted_at=typed, **{"from": "ticket"})
    assert response.status_code == status
    html = response.content.decode()
    assert message in html and "Audit trail" in html
    assert f'value="{typed}"' in html
    assert not ReportSubmission.objects.exists()


def test_over_the_ticket_page_each_thing_is_read_once(api, console, monkeypatch):
    from console import api_calls, views, views_reports

    ticket_id = _complete_ticket(api)
    calls = []

    def counting(request, method, path, **kwargs):
        calls.append((method, path))
        return api_calls.call_api(request, method, path, **kwargs)

    monkeypatch.setattr(views, "call_api", counting)
    monkeypatch.setattr(views_reports, "call_api", counting)
    page = console.get(f"/console/tickets/{ticket_id}/reports/early_warning/record?from=ticket")
    assert page.status_code == 200
    assert calls.count(("GET", "/tickets")) == 1
    assert calls.count(("GET", f"/tickets/{ticket_id}")) == 1
    assert calls.count(("GET", f"/tickets/{ticket_id}/reports/early_warning")) == 1
