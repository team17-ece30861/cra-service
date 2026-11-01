"""Console pages (4.U2 part 1): the Tickets list and the single Ticket page. They show what
the API returns, keep reporter details to the ticket page, and take "now" from the service
clock, never the browser's."""

import re

import pytest
from django.contrib.auth.models import User
from django.contrib.staticfiles import finders
from django.test import Client

from console import present
from cra_service.validation import ACTOR_HEADER

pytestmark = pytest.mark.django_db

PASSWORD = "correct horse battery"
REPORTER_NAME = "Zelda Unique-Reporter-7731"
REPORTER_CONTACT = "zelda-7731@example.invalid"
NOW = "2026-10-29T14:00:00Z"
AWARE = "2026-10-29T10:40:00Z"  # the early warning is due 24 h later: 2026-10-30T10:40:00Z


def _ticket_body(title="Heap overflow in OTA update parser", reporter=True):
    body = {
        "source": "external_researcher",
        "title": title,
        "description": "A crafted manifest overflows the parser.",
        "product": {"manufacturer": "Nordvik", "name": "Lumen Gateway 4"},
        "severity": "critical",
        "sensitivity": "AMBER",
    }
    if reporter:
        body["reporter"] = {"name": REPORTER_NAME, "contact": REPORTER_CONTACT}
    return body


@pytest.fixture
def api(authed):
    """The API with the bearer token and an actor, and the clock fixed at NOW."""
    assert (
        authed.put("/test/clock", {"now": NOW}, content_type="application/json").status_code == 200
    )
    yield authed
    authed.delete("/test/clock")


def _create(api, **kwargs):
    response = api.post(
        "/tickets",
        _ticket_body(**kwargs),
        content_type="application/json",
        headers={ACTOR_HEADER: "psirt-intake"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _triage(api, ticket_id, aware=AWARE):
    response = api.post(
        f"/tickets/{ticket_id}/triage",
        {"decision": "actively_exploited", "reason": "Confirmed in the wild.", "aware_at": aware},
        content_type="application/json",
        headers={ACTOR_HEADER: "m.okafor"},
    )
    assert response.status_code == 200


@pytest.fixture
def console():
    user = User.objects.create_user("m.okafor", password=PASSWORD)
    client = Client()
    client.force_login(user)
    return client


# --- Signed out ---


@pytest.mark.parametrize("path", ["/console/", "/console/tickets/anything"])
def test_pages_send_signed_out_people_to_sign_in(path):
    response = Client().get(path)
    assert response.status_code == 302
    assert response["Location"].startswith("/console/sign-in?next=")


# --- Tickets list ---


def test_list_shows_tickets_created_through_the_api(api, console):
    first = _create(api, title="Heap overflow in OTA update parser")
    second = _create(api, title="Path traversal in log export")
    _triage(api, first)
    html = console.get("/console/").content.decode()
    assert "Heap overflow in OTA update parser" in html
    assert "Path traversal in log export" in html
    assert f'href="/console/tickets/{first}"' in html
    assert f'href="/console/tickets/{second}"' in html
    assert "To triage" in html  # the untriaged one is grouped for triage


def test_list_never_shows_reporter_details(api, console):
    _triage(api, _create(api))
    for path in (
        "/console/",
        "/console/?view=triage",
        "/console/?view=due",
        "/console/?view=closed",
    ):
        html = console.get(path).content.decode()
        assert REPORTER_NAME not in html and REPORTER_CONTACT not in html


def test_empty_list_says_so(api, console):
    response = console.get("/console/")
    assert response.status_code == 200
    assert "No tickets yet" in response.content.decode()


def test_filters_use_the_api_and_bad_values_get_the_apis_answer(api, console):
    _create(api, title="Still waiting for triage")
    html = console.get("/console/?view=triage").content.decode()
    assert "Still waiting for triage" in html
    overdue = console.get("/console/?view=overdue").content.decode()
    assert 'class="lrow"' not in overdue and "No tickets here" in overdue
    bad = console.get("/console/?state=nonsense")
    assert bad.status_code == 400
    assert "That filter didn" in bad.content.decode()


def test_list_keeps_the_signed_in_username_on_the_page(api, console):
    html = console.get("/console/").content.decode()
    assert "Signed in as m.okafor" in html
    assert 'action="/console/sign-out"' in html and "csrfmiddlewaretoken" in html


# --- Ticket page ---


def test_ticket_page_shows_reporter_and_audit_entries(api, console):
    ticket_id = _create(api)
    _triage(api, ticket_id)
    response = console.get(f"/console/tickets/{ticket_id}")
    assert response.status_code == 200
    html = response.content.decode()
    assert REPORTER_NAME in html and REPORTER_CONTACT in html
    assert "Shown only here" in html
    assert "Triaged as actively exploited" in html and "by m.okafor" in html
    assert "Created" in html and "by psirt-intake" in html
    assert "Confirmed in the wild." in html  # the triage reason
    assert "TLP:AMBER" in html and "Actively exploited" in html


def test_audit_entries_never_carry_the_reporter(api, console):
    ticket_id = _create(api)
    html = console.get(f"/console/tickets/{ticket_id}").content.decode()
    trail = html[html.index("Audit trail") :]
    assert REPORTER_NAME not in trail


@pytest.mark.parametrize(
    "ticket_id", ["00000000-0000-0000-0000-000000000000", "not-a-ticket", "%3F"]
)
def test_unknown_ticket_is_a_not_found_page(api, console, ticket_id):
    response = console.get(f"/console/tickets/{ticket_id}")
    assert response.status_code == 404
    html = response.content.decode()
    assert "no ticket with that ID" in html
    assert response["Content-Type"].startswith("text/html")


# --- Time comes from the service clock ---


def test_pages_take_now_from_the_service_clock(api, console):
    ticket_id = _create(api)
    _triage(api, ticket_id)
    home = console.get("/console/").content.decode()
    assert 'data-now="2026-10-29T14:00:00Z"' in home
    assert "2026-10-29 14:00:00 UTC" in home
    assert "Test clock is fixed" in home
    # The early warning is due 2026-10-30T10:40:00Z: 20 h 40 m after the fixed now.
    assert 'data-hms2="2026-10-30T10:40:00Z">20:40:00<' in home
    assert "in 20 h 40 m" in home
    page = console.get(f"/console/tickets/{ticket_id}").content.decode()
    assert 'data-now="2026-10-29T14:00:00Z"' in page
    assert ">20:40:00<" in page

    api.put("/test/clock", {"now": "2026-10-30T11:40:00Z"}, content_type="application/json")
    later = console.get("/console/").content.decode()
    assert 'data-now="2026-10-30T11:40:00Z"' in later
    assert "1 h 0 m overdue" in later
    assert "Overdue" in later


def test_pages_never_read_the_browser_clock():
    js = open(finders.find("console/ledger.js")).read()
    assert "Date.now(" not in js and "new Date()" not in js


# --- Static files ---


def test_static_files_the_pages_use_exist(api, console):
    ticket_id = _create(api)
    pages = [console.get("/console/"), console.get(f"/console/tickets/{ticket_id}")]
    for page in pages:
        for path in re.findall(r'(?:src|href)="/static/([^"]+)"', page.content.decode()):
            assert finders.find(path), path
    assert finders.find("console/ledger.js") and finders.find("console/ledger.css")


# --- Presentation helpers ---


def test_countdown_text_matches_the_prototype():
    assert present.relative(6 * 3600 + 40 * 60) == "in 6 h 40 m"
    assert present.relative(42 * 3600) == "in 1 d 18 h"
    assert present.relative(-(3600 + 5 * 60)) == "1 h 5 m overdue"
    assert present.hms(6 * 3600 + 40 * 60, two=True) == "06:40:00"
    assert present.hms(19 * 3600 + 12 * 60) == "19:12:00"
    assert present.initials("m.okafor") == "MO"
    assert present.utc("2026-10-30T09:12:00Z") == "2026-10-30 09:12:00 UTC"


def test_audit_names_the_submitted_report_and_its_reference(api, console):
    ticket_id = _create(api)
    patch = api.patch(
        f"/tickets/{ticket_id}",
        {"product": {"affected_versions": ["4.1.0"]}, "member_states": ["DE"]},
        content_type="application/json",
        headers={ACTOR_HEADER: "m.okafor"},
    )
    assert patch.status_code == 200
    _triage(api, ticket_id)
    submitted = api.post(
        f"/tickets/{ticket_id}/reports/early_warning/submission",
        {"reference": "CSIRT-DE-2026-1044"},
        content_type="application/json",
        headers={ACTOR_HEADER: "j.berg"},
    )
    assert submitted.status_code == 200, submitted.content
    html = console.get(f"/console/tickets/{ticket_id}").content.decode()
    assert "Early warning submitted</b> by j.berg" in html
    assert "Reference CSIRT-DE-2026-1044" in html
    assert "affected_versions" in html  # the update's change is listed
