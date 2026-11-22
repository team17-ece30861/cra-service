"""Console sign-in lockout (LIM-12, plan 5.8): five failures for one username within 15
minutes lock it for 15 minutes from the fifth, for real and unknown usernames alike."""

import logging
from datetime import UTC, datetime, timedelta

import pytest
from django.contrib.auth.models import User
from django.test import Client

from console import lockout
from console.models import SignInFailure
from console.views import BAD_SIGN_IN
from core import clock
from tests.conftest import TOKEN

pytestmark = pytest.mark.django_db

PASSWORD = "correct horse battery"
T0 = datetime(2026, 11, 22, 12, 0, 0, tzinfo=UTC)
BAD = BAD_SIGN_IN.replace("'", "&#x27;")


@pytest.fixture
def person():
    return User.objects.create_user("m.okafor", password=PASSWORD)


@pytest.fixture(autouse=True)
def fixed_time():
    clock.fix(T0)


def at(**delta):
    clock.fix(T0 + timedelta(**delta))


def _sign_in(client, username="m.okafor", password=PASSWORD, **extra):
    return client.post("/console/sign-in", {"username": username, "password": password}, **extra)


def _fail(client, times, username="m.okafor"):
    return [_sign_in(client, username, "wrong").content.decode() for _ in range(times)]


def _signed_in(client):
    return client.get("/console/").status_code == 200


def test_four_failures_keep_the_ordinary_message(person):
    pages = _fail(Client(), 4)
    assert all(BAD in page for page in pages)
    assert not any("Too many attempts" in page for page in pages)


def test_the_fifth_failure_locks_with_the_generic_message(person):
    *_, fifth = _fail(Client(), 5)
    assert "Too many attempts. Try again in 15 minutes." in fifth
    assert 'data-error="1"' in fifth and 'class="si-group bad"' in fifth
    assert 'value="m.okafor"' in fifth


def test_the_right_password_fails_while_locked(person):
    client = Client()
    _fail(client, 5)
    at(minutes=1)
    response = _sign_in(client)
    assert response.status_code == 200
    assert "Too many attempts. Try again in 14 minutes." in response.content.decode()
    assert not _signed_in(client)


def test_minutes_round_up(person):
    client = Client()
    _fail(client, 5)
    at(minutes=14, seconds=1)
    assert "Try again in 1 minute." in _sign_in(client).content.decode()
    at(minutes=0, seconds=30)
    assert "Try again in 15 minutes." in _sign_in(client).content.decode()


def test_the_lock_ends_fifteen_minutes_after_the_fifth_failure(person):
    client = Client()
    _fail(client, 4)
    at(minutes=2)
    _fail(client, 1)  # the fifth, at 12:02; locked until 12:17
    at(minutes=16, seconds=59)
    assert "Too many attempts" in _sign_in(client).content.decode()
    assert not _signed_in(client)
    at(minutes=17)
    assert _sign_in(client).status_code == 302
    assert _signed_in(client)


def test_attempts_while_locked_do_not_extend_the_lock(person):
    client = Client()
    _fail(client, 5)
    for minute in range(1, 15):
        at(minutes=minute)
        _fail(client, 1)
    at(minutes=15)
    assert _sign_in(client).status_code == 302


def test_failures_spread_beyond_fifteen_minutes_do_not_lock(person):
    client = Client()
    for minute in (0, 4, 8, 12, 15):  # the first has aged out by the fifth
        at(minutes=minute)
        page = _fail(client, 1)[0]
    assert BAD in page
    assert _sign_in(client).status_code == 302


def test_after_the_lock_ends_counting_starts_again(person):
    client = Client()
    _fail(client, 5)
    at(minutes=15)
    pages = _fail(client, 4)
    assert all(BAD in page for page in pages)
    assert _sign_in(client).status_code == 302


def test_success_clears_the_count(person):
    client = Client()
    _fail(client, 4)
    assert _sign_in(client).status_code == 302
    assert not SignInFailure.objects.exists()
    other = Client()
    pages = _fail(other, 4)
    assert all(BAD in page for page in pages)
    assert _sign_in(other).status_code == 302


def test_unknown_usernames_lock_the_same_way(person):
    known = _fail(Client(), 5, "m.okafor")
    unknown = _fail(Client(), 5, "nobody")
    assert [BAD in page for page in unknown] == [BAD in page for page in known]
    assert "Too many attempts. Try again in 15 minutes." in unknown[-1]
    at(minutes=1)
    assert "Try again in 14 minutes." in _sign_in(Client(), "nobody").content.decode()


def test_other_usernames_are_unaffected(person):
    User.objects.create_user("j.reyes", password=PASSWORD)
    _fail(Client(), 5, "m.okafor")
    client = Client()
    assert _sign_in(client, "j.reyes").status_code == 302
    assert _signed_in(client)


def test_case_and_spaces_count_as_the_same_username(person):
    client = Client()
    for name in ("m.okafor", "M.OKAFOR", "  m.okafor ", "M.Okafor", "m.okafor\t"):
        page = _sign_in(client, name, "wrong").content.decode()
    assert "Too many attempts" in page
    assert "Too many attempts" in _sign_in(client, "m.okafor").content.decode()


def test_the_lock_is_logged_once_without_the_password(person, caplog):
    caplog.set_level(logging.INFO, logger="console.lockout")
    client = Client(REMOTE_ADDR="10.0.0.9")
    for _ in range(6):
        _sign_in(client, "M.Okafor", "hunter2-secret")
    lines = [r.getMessage() for r in caplog.records if r.name == "console.lockout"]
    assert len(lines) == 1
    assert "username='m.okafor'" in lines[0] and "client_ip='10.0.0.9'" in lines[0]
    assert "hunter2" not in caplog.text


def test_the_log_uses_the_address_cloud_run_appends(person, caplog):
    caplog.set_level(logging.INFO, logger="console.lockout")
    client = Client(REMOTE_ADDR="169.254.1.1", HTTP_X_FORWARDED_FOR="1.2.3.4, 203.0.113.7")
    _fail(client, 5)
    assert "client_ip='203.0.113.7'" in caplog.text


def test_csrf_is_still_enforced_and_rejected_posts_do_not_count(person):
    client = Client(enforce_csrf_checks=True)
    for _ in range(6):
        assert _sign_in(client, "m.okafor", "wrong").status_code == 403
    assert not SignInFailure.objects.exists()
    _fail(Client(), 5)
    assert _sign_in(client).status_code == 403


def test_empty_usernames_are_not_counted():
    for _ in range(6):
        assert BAD in _sign_in(Client(), "", "wrong").content.decode()
    assert not SignInFailure.objects.exists()


def test_the_api_is_unaffected(person):
    _fail(Client(), 5)
    api = Client(headers={"Authorization": f"Bearer {TOKEN}"})
    assert api.get("/tickets").status_code == 200


def test_reset_leaves_locks_in_place(person):
    _fail(Client(), 5)
    api = Client(headers={"Authorization": f"Bearer {TOKEN}"})
    assert api.post("/test/reset").status_code == 204
    assert "Too many attempts" in _sign_in(Client()).content.decode()


def test_a_test_clock_moved_back_ignores_later_rows(person):
    client = Client()
    _fail(client, 5)
    clock.fix(T0 - timedelta(hours=1))
    assert _sign_in(client).status_code == 302


def test_old_rows_are_pruned_on_write(person):
    _fail(Client(), 3, "nobody")
    at(minutes=15)
    _fail(Client(), 1)
    assert list(SignInFailure.objects.values_list("username", flat=True)) == ["m.okafor"]


def test_username_key_normalizes_like_the_sign_in_form():
    assert lockout.username_key("  M.Okafor\t") == "m.okafor"
    assert lockout.username_key("ｍ.okafor") == "m.okafor"  # fullwidth m, NFKC
    assert lockout.username_key("a\x00b") == "ab"
    assert len(lockout.username_key("x" * 1000)) == 150
    assert lockout.username_key("   ") == ""
