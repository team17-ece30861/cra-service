import re
from datetime import UTC, datetime

import pytest

from core import clock
from core.models import FixedClock
from tests.problems import assert_problem

pytestmark = pytest.mark.django_db

UTC_SECOND = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
REAL = datetime(2026, 10, 5, 9, 0, 0, 987_654, tzinfo=UTC)


@pytest.fixture
def real_time(monkeypatch):
    """Pin the system clock that core.clock reads when no time is fixed."""
    monkeypatch.setattr("core.clock.timezone.now", lambda: REAL)
    return REAL


def _put(client, now):
    return client.put("/test/clock", {"now": now}, content_type="application/json")


# --- core.clock -------------------------------------------------------------------


def test_now_is_real_utc_time_truncated_to_the_second(real_time):
    assert clock.now() == datetime(2026, 10, 5, 9, 0, 0, tzinfo=UTC)


def test_now_without_patching_is_aware_utc_to_the_second():
    now = clock.now()
    assert now.utcoffset().total_seconds() == 0
    assert now.microsecond == 0


def test_fix_and_release(real_time):
    fixed = clock.fix(datetime(2030, 1, 1, 12, 0, 0, 500, tzinfo=UTC))
    assert fixed == datetime(2030, 1, 1, 12, 0, 0, tzinfo=UTC)
    assert clock.now() == fixed
    assert clock.now() == fixed
    clock.release()
    assert clock.now() == datetime(2026, 10, 5, 9, 0, 0, tzinfo=UTC)


def test_fix_replaces_an_earlier_fixed_time():
    clock.fix(datetime(2030, 1, 1, tzinfo=UTC))
    clock.fix(datetime(2031, 1, 1, tzinfo=UTC))
    assert clock.now() == datetime(2031, 1, 1, tzinfo=UTC)
    assert FixedClock.objects.count() == 1


# --- GET /test/clock ------------------------------------------------------------


def test_get_returns_real_time_when_not_fixed(authed, real_time):
    response = authed.get("/test/clock")
    assert response.status_code == 200
    assert response.json() == {"now": "2026-10-05T09:00:00Z"}


def test_get_returns_utc_to_the_second(authed):
    response = authed.get("/test/clock")
    assert UTC_SECOND.fullmatch(response.json()["now"])


# --- PUT /test/clock ------------------------------------------------------------


def test_put_fixes_the_clock(authed):
    response = _put(authed, "2026-10-02T17:00:00Z")
    assert response.status_code == 200
    assert response.json() == {"now": "2026-10-02T17:00:00Z"}


def test_two_reads_after_put_are_identical(authed, monkeypatch):
    _put(authed, "2026-10-02T17:00:00Z")
    first = authed.get("/test/clock").json()
    # Even if real time moves on between the reads, the fixed clock doesn't.
    monkeypatch.setattr("core.clock.timezone.now", lambda: datetime(2040, 1, 1, tzinfo=UTC))
    second = authed.get("/test/clock").json()
    assert first == second == {"now": "2026-10-02T17:00:00Z"}


def test_put_normalizes_offset_and_fraction(authed):
    response = _put(authed, "2026-10-02T19:00:00.999+02:00")
    assert response.json() == {"now": "2026-10-02T17:00:00Z"}
    assert authed.get("/test/clock").json() == {"now": "2026-10-02T17:00:00Z"}


def test_put_again_moves_the_fixed_clock(authed):
    _put(authed, "2026-10-02T17:00:00Z")
    _put(authed, "2026-10-01T08:00:00Z")  # backwards is allowed
    assert authed.get("/test/clock").json() == {"now": "2026-10-01T08:00:00Z"}


@pytest.mark.parametrize(
    "body,field,message",
    [
        ({"now": "2026-10-02T17:00Z"}, "now", "must include seconds"),
        ({"now": "2026-10-02T17:00:00"}, "now", "must include a UTC offset (Z or +hh:mm)"),
        ({"now": None}, "now", "must be an RFC 3339 timestamp such as 2026-10-05T09:00:00Z"),
        ({"now": 1759654800}, "now", "must be an RFC 3339 timestamp such as 2026-10-05T09:00:00Z"),
        ({}, "now", "required"),
        ({"now": "2026-10-02T17:00:00Z", "frozen": True}, "frozen", "not allowed"),
    ],
)
def test_put_rejects_invalid_bodies_and_changes_nothing(authed, body, field, message):
    _put(authed, "2026-10-02T17:00:00Z")
    response = authed.put("/test/clock", body, content_type="application/json")
    problem = assert_problem(response, 400, "Invalid request")
    assert {"field": field, "message": message} in problem["errors"]
    assert authed.get("/test/clock").json() == {"now": "2026-10-02T17:00:00Z"}


# --- DELETE /test/clock ---------------------------------------------------------


def test_delete_releases_the_clock(authed, real_time):
    _put(authed, "2026-10-02T17:00:00Z")
    response = authed.delete("/test/clock")
    assert response.status_code == 204
    assert response.content == b""
    assert authed.get("/test/clock").json() == {"now": "2026-10-05T09:00:00Z"}


def test_delete_when_not_fixed_is_204(authed):
    assert authed.delete("/test/clock").status_code == 204
