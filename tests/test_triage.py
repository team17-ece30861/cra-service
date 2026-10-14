"""Database-free tests for the domain parts of Phase 3 triage acceptance."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from core.domain.triage import TriageResult, triage_ticket
from cra_service.errors import BadRequest, Conflict, RuleViolation

NOW = datetime(2026, 10, 5, 9, tzinfo=UTC)


def test_active_exploitation_moves_received_ticket_to_reportable():
    # Model D E1: awareness predates Monday triage (and may predate receipt).
    aware_at = datetime(2026, 10, 2, 17, tzinfo=UTC)

    assert triage_ticket(
        state="received", decision="actively_exploited", now=NOW, aware_at=aware_at
    ) == TriageResult(state="reportable", resolution=None, aware_at=aware_at)


def test_awareness_exactly_at_current_time_is_allowed():
    assert (
        triage_ticket(
            state="received", decision="actively_exploited", now=NOW, aware_at=NOW
        ).aware_at
        == NOW
    )


def test_awareness_one_second_in_the_future_is_a_rule_violation():
    # Model D E8 and AC-04.
    with pytest.raises(RuleViolation) as excinfo:
        triage_ticket(
            state="received",
            decision="actively_exploited",
            now=NOW,
            aware_at=NOW + timedelta(seconds=1),
        )

    assert excinfo.value.status == 422
    assert excinfo.value.errors == [{"field": "aware_at", "message": "must not be later than now"}]


def test_missing_awareness_is_a_bad_request():
    with pytest.raises(BadRequest) as excinfo:
        triage_ticket(state="received", decision="actively_exploited", now=NOW)

    assert excinfo.value.status == 400
    assert excinfo.value.errors == [
        {"field": "aware_at", "message": "required when decision is actively_exploited"}
    ]


@pytest.mark.parametrize("decision", ["not_actively_exploited", "invalid"])
def test_non_reportable_decisions_close_with_the_corresponding_resolution(decision):
    assert triage_ticket(state="received", decision=decision, now=NOW) == TriageResult(
        state="closed", resolution=decision, aware_at=None
    )


@pytest.mark.parametrize("state", ["reportable", "closed"])
@pytest.mark.parametrize("decision", ["actively_exploited", "not_actively_exploited", "invalid"])
def test_triage_is_rejected_after_ticket_leaves_received(state, decision):
    with pytest.raises(Conflict) as excinfo:
        triage_ticket(state=state, decision=decision, now=NOW, aware_at=NOW)

    assert excinfo.value.status == 409


def test_missing_awareness_takes_precedence_over_state_conflict():
    with pytest.raises(BadRequest):
        triage_ticket(state="closed", decision="actively_exploited", now=NOW)


def test_state_conflict_takes_precedence_over_future_awareness():
    with pytest.raises(Conflict):
        triage_ticket(
            state="reportable",
            decision="actively_exploited",
            now=NOW,
            aware_at=NOW + timedelta(seconds=1),
        )


@pytest.mark.parametrize("state", ["received", "reportable", "closed"])
def test_unknown_decision_is_rejected_before_state_checks(state):
    with pytest.raises(BadRequest) as excinfo:
        triage_ticket(state=state, decision="unverified", now=NOW)

    assert excinfo.value.status == 400
    assert excinfo.value.errors[0]["field"] == "decision"


def test_awareness_offset_is_normalized_to_utc():
    # Model D E7; awareness's local hour must not be mistaken for a future time.
    aware_at = datetime(2026, 10, 5, 11, tzinfo=timezone(timedelta(hours=2)))

    result = triage_ticket(
        state="received", decision="actively_exploited", now=NOW, aware_at=aware_at
    )

    assert result.aware_at == NOW
    assert result.aware_at.tzinfo is UTC


def test_current_time_offset_is_normalized_before_future_check():
    local_now = datetime(2026, 10, 5, 4, tzinfo=timezone(timedelta(hours=-5)))

    result = triage_ticket(
        state="received", decision="actively_exploited", now=local_now, aware_at=NOW
    )

    assert result.aware_at == NOW


def test_fractional_seconds_are_truncated_before_comparing():
    result = triage_ticket(
        state="received",
        decision="actively_exploited",
        now=NOW.replace(microsecond=100_000),
        aware_at=NOW.replace(microsecond=999_999),
    )

    assert result.aware_at == NOW
    assert result.aware_at.microsecond == 0


@pytest.mark.parametrize("field", ["now", "aware_at"])
def test_naive_datetimes_are_rejected_at_the_domain_boundary(field):
    times = {"now": NOW, "aware_at": NOW}
    times[field] = NOW.replace(tzinfo=None)

    with pytest.raises(ValueError, match="timezone-aware"):
        triage_ticket(state="received", decision="actively_exploited", **times)
