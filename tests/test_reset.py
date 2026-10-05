from datetime import UTC, datetime

import pytest

from core import clock, controls
from core.models import FixedClock

pytestmark = pytest.mark.django_db


def test_reset_returns_204_with_no_body(authed):
    response = authed.post("/test/reset")
    assert response.status_code == 204
    assert response.content == b""


def test_reset_keeps_the_fixed_clock(authed):
    authed.put("/test/clock", {"now": "2026-10-02T17:00:00Z"}, content_type="application/json")
    assert authed.post("/test/reset").status_code == 204
    assert authed.get("/test/clock").json() == {"now": "2026-10-02T17:00:00Z"}


def test_reset_clears_every_application_model_except_the_clock():
    # New models in core are cleared automatically; only the clock is kept.
    assert FixedClock not in controls.reset_models()


def test_reset_deletes_the_rows_of_every_model_it_clears(authed, monkeypatch):
    # Exercise the TRUNCATE path with the only table that exists today.
    monkeypatch.setattr(controls, "KEPT_ON_RESET", set())
    clock.fix(datetime(2030, 1, 1, tzinfo=UTC))
    assert authed.post("/test/reset").status_code == 204
    assert not FixedClock.objects.exists()


def test_reset_is_idempotent(authed):
    assert authed.post("/test/reset").status_code == 204
    assert authed.post("/test/reset").status_code == 204
