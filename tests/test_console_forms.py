"""Console sheets (4.U2 part 2): New Ticket, Edit Ticket and Triage. Each POST makes one
change through the API as the signed-in person; when the API says no, the sheet comes back
with the input kept and the API's errors under the fields, and nothing changes."""

import json
from datetime import UTC, datetime

import pytest
from django.contrib.auth.models import User
from django.test import Client

from console import forms
from core.domain.deadlines import calculate_deadlines
from core.models import AuditEntry, Ticket
from cra_service.validation import ACTOR_HEADER

pytestmark = pytest.mark.django_db

PASSWORD = "correct horse battery"
NOW = "2026-10-29T14:00:00Z"


@pytest.fixture
def api(authed):
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


def _create(api, **extra):
    body = {
        "source": "customer",
        "title": "Path traversal in log export",
        "description": "Log export follows ../ in file names.",
        "product": {"manufacturer": "Ostrava", "name": "NAS 2"},
        "reporter": {"name": "Reporter Person", "contact": "rp@example.invalid"},
        **extra,
    }
    response = api.post(
        "/tickets", body, content_type="application/json", headers={ACTOR_HEADER: "intake"}
    )
    assert response.status_code == 201
    return response.json()["id"]


def _toast(response):
    return [json.loads(m.message) for m in response.wsgi_request._messages]


NEW = {
    "title": "Heap overflow in OTA update parser",
    "source": "external_researcher",
    "product.manufacturer": "Nordvik Devices",
    "product.name": "Lumen Gateway 4",
    "product.affected_versions": "4.1.0\n4.1.1",
    "description": "A crafted manifest overflows the parser.",
    "reporter.name": "J. Doe",
    "reporter.contact": "",
    "member_states": "DE\nNL",
    "severity": "high",
    "vulnerability.cve_id": "CVE-2026-12345",
    "fix.available_at": "2026-10-28 09:00:00",
}


# --- Signed out, CSRF ---


@pytest.mark.parametrize(
    "path", ["/console/tickets/new", "/console/tickets/x/edit", "/console/tickets/x/triage"]
)
def test_sheets_send_signed_out_people_to_sign_in(path):
    for response in (Client().get(path), Client().post(path, {})):
        assert response.status_code == 302
        assert response["Location"].startswith("/console/sign-in?next=")
    assert Ticket.objects.count() == 0


def test_posts_need_the_csrf_token(api):
    user = User.objects.create_user("m.okafor", password=PASSWORD)
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    ticket_id = _create(api)
    assert client.post("/console/tickets/new", NEW).status_code == 403
    assert client.post(f"/console/tickets/{ticket_id}/edit", {"title": "x"}).status_code == 403
    triage = {"decision": "invalid", "reason": "Not ours."}
    assert client.post(f"/console/tickets/{ticket_id}/triage", triage).status_code == 403
    assert Ticket.objects.count() == 1
    assert Ticket.objects.get().state == "received"
    assert AuditEntry.objects.count() == 1


# --- New Ticket ---


def test_new_ticket_page_is_the_list_with_the_sheet_open(api, console):
    html = console.get("/console/tickets/new").content.decode()
    assert 'class="sheet-layer open entering"' in html
    assert 'id="sheet-new"' in html and "New Ticket" in html
    assert 'action="/console/tickets/new"' in html
    assert "console/forms.css" in html and "console/forms.js" in html


def test_new_ticket_creates_it_as_the_signed_in_person(api, console):
    response = console.post("/console/tickets/new", NEW)
    ticket = Ticket.objects.get()
    assert response.status_code == 302
    assert response["Location"] == f"/console/tickets/{ticket.pk}"
    assert ticket.state == "received"
    assert ticket.data["product"]["affected_versions"] == ["4.1.0", "4.1.1"]
    assert ticket.data["member_states"] == ["DE", "NL"]
    assert ticket.data["reporter"] == {"name": "J. Doe"}
    assert ticket.data["fix"] == {"available_at": "2026-10-28T09:00:00Z"}
    assert "impact" not in ticket.data  # empty fields aren't sent
    entry = ticket.audit_entries.get()
    assert (entry.actor, entry.action) == ("m.okafor", "created")
    assert _toast(response)[0]["title"] == "Ticket created"
    page = console.get(response["Location"]).content.decode()
    assert "data-flash=" in page and "Ticket created" in page


def test_new_ticket_error_keeps_the_input_and_shows_the_field_error(api, console):
    bad = {**NEW, "title": "", "vulnerability.cve_id": "CVE-26-1"}
    response = console.post("/console/tickets/new", bad)
    assert response.status_code == 400
    assert Ticket.objects.count() == 0 and AuditEntry.objects.count() == 0
    html = response.content.decode()
    assert 'class="sheet-layer open"' in html  # already open: no second entrance
    assert "Enter a title." in html
    assert "Use the format CVE-2026-12345." in html
    assert 'value="Lumen Gateway 4"' in html and 'value="CVE-26-1"' in html
    assert 'class="input invalid" id="tn-ttl"' in html


# --- Edit Ticket ---


def test_edit_page_is_the_ticket_with_the_sheet_open_and_focus(api, console):
    ticket_id = _create(api)
    html = console.get(f"/console/tickets/{ticket_id}/edit?focus=member_states").content.decode()
    assert 'id="sheet-edit"' in html and "Edit Ticket" in html
    assert 'class="field wanted" data-field="member_states"' in html
    assert 'value="Reporter Person"' in html  # reporter details: the ticket page and its sheet


def test_edit_sends_only_changed_fields_and_records_the_actor(api, console):
    ticket_id = _create(api, impact="Reads any file.")
    current = forms.values_from_ticket(api.get(f"/tickets/{ticket_id}").json())
    post = {k: "\n".join(v) if isinstance(v, list) else v for k, v in current.items()}
    post.update({"title": "Path traversal in log export (v2)", "member_states": "DE", "impact": ""})
    response = console.post(f"/console/tickets/{ticket_id}/edit", post)
    assert response.status_code == 302
    ticket = Ticket.objects.get(pk=ticket_id)
    assert ticket.data["title"] == "Path traversal in log export (v2)"
    assert ticket.data["member_states"] == ["DE"]
    assert ticket.data.get("impact") is None
    entry = ticket.audit_entries.last()
    assert (entry.actor, entry.action) == ("m.okafor", "updated")
    assert {c["field"] for c in entry.changes} == {"title", "member_states", "impact"}
    assert _toast(response)[0]["body"].startswith("3 fields changed.")


def test_edit_aware_without_a_reason_shows_the_apis_error_and_changes_nothing(api, console):
    ticket_id = _create(api)
    api.post(
        f"/tickets/{ticket_id}/triage",
        {"decision": "actively_exploited", "aware_at": "2026-10-29T10:00:00Z", "reason": "Seen."},
        content_type="application/json",
        headers={ACTOR_HEADER: "intake"},
    )
    current = forms.values_from_ticket(api.get(f"/tickets/{ticket_id}").json())
    post = {k: "\n".join(v) if isinstance(v, list) else v for k, v in current.items()}
    post["aware_at"] = "2026-10-29 09:00:00"
    response = console.post(f"/console/tickets/{ticket_id}/edit", post)
    assert response.status_code == 422
    assert "Enter a reason." in response.content.decode()
    ticket = Ticket.objects.get(pk=ticket_id)
    assert ticket.aware_at.isoformat() == "2026-10-29T10:00:00+00:00"
    assert ticket.audit_entries.count() == 2


def test_edit_with_nothing_changed_makes_no_call(api, console):
    ticket_id = _create(api)
    current = forms.values_from_ticket(api.get(f"/tickets/{ticket_id}").json())
    post = {k: "\n".join(v) if isinstance(v, list) else v for k, v in current.items()}
    response = console.post(f"/console/tickets/{ticket_id}/edit", post)
    assert response.status_code == 200
    assert "Change a field to save." in response.content.decode()
    assert AuditEntry.objects.count() == 1


def test_edit_closed_ticket_shows_the_apis_conflict(api, console):
    ticket_id = _create(api)
    console.post(f"/console/tickets/{ticket_id}/triage", {"decision": "invalid", "reason": "No."})
    current = forms.values_from_ticket(api.get(f"/tickets/{ticket_id}").json())
    post = {k: "\n".join(v) if isinstance(v, list) else v for k, v in current.items()}
    response = console.post(f"/console/tickets/{ticket_id}/edit", {**post, "title": "New title"})
    assert response.status_code == 409
    assert "A closed ticket cannot be changed." in response.content.decode()
    assert Ticket.objects.get(pk=ticket_id).data["title"] == "Path traversal in log export"


# --- Triage ---


def test_triage_page_shows_the_decisions_and_the_domain_offsets(api, console):
    ticket_id = _create(api)
    html = console.get(f"/console/tickets/{ticket_id}/triage").content.decode()
    assert 'id="sheet-triage"' in html
    for value in forms.DECISIONS:
        assert f'value="{value}"' in html
    # The preview's offsets are the domain's own (core/domain/deadlines.py)
    aware = datetime(2026, 10, 29, 10, 40, tzinfo=UTC)
    d = calculate_deadlines(aware)
    ew, n = (int((x - aware).total_seconds()) for x in (d.early_warning_due, d.notification_due))
    assert f'"early_warning": {ew}' in html and f'"notification": {n}' in html


def test_triage_actively_exploited(api, console):
    ticket_id = _create(api)
    response = console.post(
        f"/console/tickets/{ticket_id}/triage",
        {"decision": "actively_exploited", "aware_at": "2026-10-29 10:40:00", "reason": "Seen."},
    )
    assert response.status_code == 302
    ticket = Ticket.objects.get(pk=ticket_id)
    assert ticket.state == "reportable"
    assert ticket.aware_at.isoformat() == "2026-10-29T10:40:00+00:00"
    entry = ticket.audit_entries.last()
    assert (entry.actor, entry.action, entry.reason) == ("m.okafor", "triaged", "Seen.")
    assert "Early warning due 2026-10-30 10:40:00 UTC." in _toast(response)[0]["body"]


@pytest.mark.parametrize("decision", ["not_actively_exploited", "invalid"])
def test_triage_closing_decisions(api, console, decision):
    ticket_id = _create(api)
    response = console.post(
        f"/console/tickets/{ticket_id}/triage",
        {"decision": decision, "aware_at": "2026-10-29 10:40:00", "reason": "Checked."},
    )
    assert response.status_code == 302
    ticket = Ticket.objects.get(pk=ticket_id)
    assert (ticket.state, ticket.resolution, ticket.aware_at) == ("closed", decision, None)
    assert _toast(response)[0]["title"] == f"Closed as {decision.replace('_', ' ')}"


def test_invalid_triage_shows_the_error_and_changes_nothing(api, console):
    ticket_id = _create(api)
    response = console.post(
        f"/console/tickets/{ticket_id}/triage",
        {"decision": "actively_exploited", "aware_at": "", "reason": "Seen in the wild."},
    )
    assert response.status_code == 400
    html = response.content.decode()
    assert "Enter when your team became aware. Deadlines count from it." in html
    assert "Seen in the wild." in html  # the reason is kept
    assert 'value="actively_exploited" checked' in html
    ticket = Ticket.objects.get(pk=ticket_id)
    assert ticket.state == "received"
    assert not ticket.audit_entries.filter(action="triaged").exists()


def test_triage_later_than_now_is_the_apis_rule(api, console):
    ticket_id = _create(api)
    response = console.post(
        f"/console/tickets/{ticket_id}/triage",
        {"decision": "actively_exploited", "aware_at": "2026-10-29 15:00:00", "reason": "x"},
    )
    assert response.status_code == 422
    assert "Enter a time at or before 2026-10-29 14:00:00 UTC." in response.content.decode()
    assert Ticket.objects.get(pk=ticket_id).state == "received"


def test_triage_twice_shows_the_conflict(api, console):
    ticket_id = _create(api)
    url = f"/console/tickets/{ticket_id}/triage"
    console.post(url, {"decision": "invalid", "reason": "No."})
    response = console.post(url, {"decision": "invalid", "reason": "Again."})
    assert response.status_code == 409
    assert "Only a received ticket can be triaged." in response.content.decode()
    assert Ticket.objects.get(pk=ticket_id).audit_entries.count() == 2


def test_sheets_for_unknown_tickets_are_not_found(api, console):
    for path in ("/console/tickets/nope/edit", "/console/tickets/nope/triage"):
        assert console.get(path).status_code == 404
        assert console.post(path, {"title": "x"}).status_code == 404


def test_list_never_carries_reporter_details_in_its_sheet(api, console):
    _create(api)
    html = console.get("/console/tickets/new").content.decode()
    assert "Reporter Person" not in html and "rp@example.invalid" not in html


def test_clearing_one_field_of_a_group_says_what_works(api, console):
    ticket_id = _create(api, vulnerability={"cve_id": "CVE-2026-12345", "description": "Path."})
    current = forms.values_from_ticket(api.get(f"/tickets/{ticket_id}").json())
    post = {k: "\n".join(v) if isinstance(v, list) else v for k, v in current.items()}
    response = console.post(
        f"/console/tickets/{ticket_id}/edit", {**post, "vulnerability.cve_id": ""}
    )
    assert response.status_code == 400
    assert "This can&#x27;t be cleared while other vulnerability details are filled in." in (
        response.content.decode()
    )
    assert Ticket.objects.get(pk=ticket_id).data["vulnerability"]["cve_id"] == "CVE-2026-12345"


def test_a_failed_read_before_a_change_shows_the_error_page(api, console, monkeypatch):
    from console import views_forms
    from console.api_calls import ApiResult, call_api

    ticket_id = _create(api)

    def failing(request, method, path, **kwargs):
        if method == "GET" and path == f"/tickets/{ticket_id}":
            return ApiResult(503, None)
        return call_api(request, method, path, **kwargs)

    monkeypatch.setattr(views_forms, "call_api", failing)
    response = console.post(
        f"/console/tickets/{ticket_id}/triage", {"decision": "invalid", "reason": "No."}
    )
    assert response.status_code == 503
    assert "Something went wrong" in response.content.decode()
    assert Ticket.objects.get(pk=ticket_id).state == "received"
