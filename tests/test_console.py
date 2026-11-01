"""Console sign-in (4.U1): session sign-in for console pages, the API untouched, and
console changes made through the API's own code as the signed-in person."""

import pytest
from django.contrib.auth.models import User
from django.test import Client, RequestFactory

from console.api_calls import call_api
from console.views import BAD_SIGN_IN, WAS_SIGNED_IN_COOKIE
from core.models import AuditEntry, Ticket
from tests.conftest import TOKEN

pytestmark = pytest.mark.django_db

PASSWORD = "correct horse battery"
PARTIAL = "00000000-0000-0000-0000-00000000beef"
TICKET = {
    "source": "external_researcher",
    "title": "Authentication bypass",
    "description": "Simulated vulnerability for console tests.",
    "product": {"manufacturer": "Acme", "name": "Router OS", "affected_versions": ["4.1.0"]},
    "reporter": {"name": "Simulated Reporter", "contact": "reporter@example.invalid"},
}


@pytest.fixture
def person():
    return User.objects.create_user("m.okafor", password=PASSWORD)


def _sign_in(client, username="m.okafor", password=PASSWORD, **extra):
    return client.post("/console/sign-in", {"username": username, "password": password, **extra})


# --- Reaching console pages ---


def test_console_pages_need_no_token_and_send_people_to_sign_in():
    response = Client().get("/console/")
    assert response.status_code == 302
    assert response["Location"] == "/console/sign-in?next=%2Fconsole%2F"


def test_console_without_slash_redirects():
    response = Client().get("/console")
    assert response.status_code in (301, 302)
    assert response["Location"] == "/console/"


def test_sign_in_page_renders_the_form():
    response = Client().get("/console/sign-in")
    assert response.status_code == 200
    html = response.content.decode()
    assert 'name="username"' in html and 'name="password"' in html
    assert "csrfmiddlewaretoken" in html
    assert "Signed out." not in html


@pytest.mark.parametrize("path", ["/consolex", "/console-admin/", "/consoles/"])
def test_only_the_exact_console_prefix_skips_the_token(path):
    assert Client().get(path).status_code == 401


def test_static_files_skip_the_token():
    assert Client().get("/static/console/ledger.css").status_code != 401


# --- Signing in ---


def test_right_password_signs_in_and_lands_on_tickets(person):
    client = Client()
    response = _sign_in(client)
    assert response.status_code == 302
    assert response["Location"] == "/console/"
    page = client.get("/console/")
    assert page.status_code == 200
    assert "Signed in as m.okafor" in page.content.decode()


def test_sign_in_returns_to_the_page_asked_for(person):
    response = _sign_in(Client(), next="/console/?x=1")
    assert response["Location"] == "/console/?x=1"


@pytest.mark.parametrize(
    "next_url",
    [
        "https://evil.example/",
        "//evil.example/",
        "/tickets",
        "/admin/",
        "/console/../admin/",
        "/console/%2e%2e/tickets",
    ],
)
def test_sign_in_never_redirects_outside_the_console(person, next_url):
    response = _sign_in(Client(), next=next_url)
    assert response["Location"] == "/console/"


@pytest.mark.parametrize(
    "username,password",
    [("m.okafor", "wrong"), ("nobody", PASSWORD), ("m.okafor", ""), ("", "")],
)
def test_wrong_details_get_one_message_that_does_not_say_which(person, username, password):
    client = Client()
    response = _sign_in(client, username, password)
    assert response.status_code == 200
    html = response.content.decode()
    assert BAD_SIGN_IN.replace("'", "&#x27;") in html
    assert 'data-error="1"' in html
    assert client.get("/console/").status_code == 302


def test_wrong_password_keeps_the_username_but_never_the_password(person):
    html = _sign_in(Client(), "m.okafor", "wrong-secret").content.decode()
    assert 'value="m.okafor"' in html
    assert "wrong-secret" not in html


def test_inactive_accounts_cannot_sign_in(person):
    person.is_active = False
    person.save()
    response = _sign_in(Client())
    assert response.status_code == 200
    assert 'data-error="1"' in response.content.decode()


def test_sign_in_needs_the_csrf_token(person):
    client = Client(enforce_csrf_checks=True)
    assert _sign_in(client).status_code == 403


def test_sessions_last_twelve_hours_and_stay_on_console_paths(settings, person):
    assert settings.SESSION_COOKIE_AGE == 12 * 3600
    client = Client()
    _sign_in(client)
    cookie = client.cookies[settings.SESSION_COOKIE_NAME]
    assert cookie["path"] == "/console/"
    assert cookie["max-age"] == 12 * 3600
    assert cookie["httponly"]


# --- Signing out ---


def test_sign_out_is_post_only(person):
    client = Client()
    _sign_in(client)
    assert client.get("/console/sign-out").status_code == 405


def test_sign_out_ends_the_session_and_shows_the_island(person):
    client = Client()
    _sign_in(client)
    response = client.post("/console/sign-out")
    assert response["Location"] == "/console/sign-in?signed-out=1"
    assert client.get("/console/").status_code == 302
    page = client.get(response["Location"])
    assert "Signed out." in page.content.decode()


def test_an_ended_session_shows_the_island(person, settings):
    client = Client()
    _sign_in(client)
    assert client.cookies[WAS_SIGNED_IN_COOKIE].value == "1"
    client.cookies.pop(settings.SESSION_COOKIE_NAME)  # the session expired
    response = client.get("/console/")
    assert response["Location"] == "/console/sign-in?next=%2Fconsole%2F&signed-out=1"
    assert "Signed out." in client.get(response["Location"]).content.decode()


# --- The API stays as it is ---


def test_a_session_never_unlocks_the_api(person):
    client = Client()
    _sign_in(client)
    for path in ("/tickets", "/test/clock", "/docs"):
        assert client.get(path).status_code == 401


def test_the_api_still_works_with_the_token():
    response = Client(headers={"Authorization": f"Bearer {TOKEN}"}).get("/tickets")
    assert response.status_code == 200


# --- Console changes go through the API's own code ---


def _console_request(user):
    request = RequestFactory().get("/console/")
    request.user = user
    return request


def test_console_changes_record_the_username_as_actor(person):
    result = call_api(_console_request(person), "POST", "/tickets", body=TICKET)
    assert result.status == 201
    entry = AuditEntry.objects.get(ticket_id=result.data["id"])
    assert entry.actor == "m.okafor"


def test_a_failed_console_change_changes_nothing(person):
    result = call_api(_console_request(person), "POST", "/tickets", body={**TICKET, "title": ""})
    assert result.status == 400
    assert result.data["errors"]
    assert not Ticket.objects.exists()
    assert not AuditEntry.objects.exists()


def test_a_change_that_fails_after_writing_is_rolled_back(person, monkeypatch):
    """The savepoint itself: a view that writes and then answers with an error leaves
    nothing behind, even inside the request's own transaction."""
    from django.http import HttpResponse
    from django.urls import ResolverMatch
    from django.utils import timezone  # test data only; the API's own clock isn't involved

    from console import api_calls

    def writes_then_fails(request):
        Ticket.objects.create(id=PARTIAL, received_at=timezone.now(), data={})
        return HttpResponse(status=422)

    monkeypatch.setattr(api_calls, "resolve", lambda path: ResolverMatch(writes_then_fails, (), {}))
    result = call_api(_console_request(person), "POST", "/tickets", body=TICKET)
    assert result.status == 422
    assert not Ticket.objects.filter(id=PARTIAL).exists()


@pytest.mark.parametrize("path", ["/test/reset", "/tester/test/run", "/health", "/ticketsx"])
def test_console_only_calls_ticket_operations(person, path):
    with pytest.raises(ValueError):
        call_api(_console_request(person), "POST", path)


def test_console_reads_match_the_api(person):
    created = call_api(_console_request(person), "POST", "/tickets", body=TICKET).data
    result = call_api(_console_request(person), "GET", f"/tickets/{created['id']}")
    assert result.status == 200
    assert result.data["reporter"]["name"] == "Simulated Reporter"
    listed = call_api(_console_request(person), "GET", "/tickets", query={"state": "received"})
    assert [t["id"] for t in listed.data] == [created["id"]]
    assert "reporter" not in listed.data[0]
