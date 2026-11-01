"""Status rules from Model B, including the Model D E6 boundary."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from core.domain.statuses import submitted_report_status, unsubmitted_obligation_status

DUE = datetime(2026, 10, 6, 9, tzinfo=UTC)
REPORT_TYPES = ["early_warning", "notification", "final_report"]


@pytest.mark.parametrize("report_type", REPORT_TYPES)
@pytest.mark.parametrize("due_at", [None, DUE])
def test_non_applicable_obligation_has_no_reporting_status(report_type, due_at):
    assert (
        unsubmitted_obligation_status(
            report_type=report_type, applicable=False, due_at=due_at, now=DUE + timedelta(days=30)
        )
        == "not_applicable"
    )


def test_final_report_awaits_fix_until_a_deadline_exists():
    assert (
        unsubmitted_obligation_status(
            report_type="final_report", applicable=True, due_at=None, now=DUE
        )
        == "awaiting_fix"
    )


@pytest.mark.parametrize("report_type", REPORT_TYPES)
@pytest.mark.parametrize(
    "now,expected",
    [
        (DUE - timedelta(seconds=1), "pending"),
        (DUE, "pending"),
        (DUE + timedelta(seconds=1), "overdue"),
    ],
    ids=["one-second-before", "exactly-due", "one-second-after"],
)
def test_unsubmitted_status_at_the_due_time_boundary(report_type, now, expected):
    assert (
        unsubmitted_obligation_status(report_type=report_type, applicable=True, due_at=DUE, now=now)
        == expected
    )


def test_changing_the_clock_recalculates_status_in_both_directions():
    inputs = {"report_type": "early_warning", "applicable": True, "due_at": DUE}

    assert unsubmitted_obligation_status(**inputs, now=DUE) == "pending"
    assert unsubmitted_obligation_status(**inputs, now=DUE + timedelta(seconds=1)) == "overdue"
    assert unsubmitted_obligation_status(**inputs, now=DUE - timedelta(seconds=1)) == "pending"


def test_recording_a_fix_starts_final_report_deadline_tracking():
    inputs = {"report_type": "final_report", "applicable": True, "now": DUE}

    assert unsubmitted_obligation_status(**inputs, due_at=None) == "awaiting_fix"
    assert unsubmitted_obligation_status(**inputs, due_at=DUE + timedelta(days=14)) == "pending"
    assert unsubmitted_obligation_status(**inputs, due_at=DUE - timedelta(seconds=1)) == "overdue"


def test_changing_the_deadline_recalculates_status():
    inputs = {"report_type": "notification", "applicable": True, "now": DUE}

    assert unsubmitted_obligation_status(**inputs, due_at=DUE - timedelta(seconds=1)) == "overdue"
    assert unsubmitted_obligation_status(**inputs, due_at=DUE) == "pending"


@pytest.mark.parametrize(
    "now,expected",
    [
        (datetime(2026, 10, 6, 4, tzinfo=timezone(timedelta(hours=-5))), "pending"),
        (datetime(2026, 10, 6, 4, 0, 1, tzinfo=timezone(timedelta(hours=-5))), "overdue"),
    ],
    ids=["equal-instant", "later-instant"],
)
def test_offsets_are_normalized_before_comparison(now, expected):
    due_at = datetime(2026, 10, 6, 11, tzinfo=timezone(timedelta(hours=2)))

    assert (
        unsubmitted_obligation_status(
            report_type="early_warning", applicable=True, due_at=due_at, now=now
        )
        == expected
    )


def test_fractional_seconds_are_truncated_before_comparison():
    assert (
        unsubmitted_obligation_status(
            report_type="early_warning",
            applicable=True,
            due_at=DUE.replace(microsecond=100_000),
            now=DUE.replace(microsecond=999_999),
        )
        == "pending"
    )


@pytest.mark.parametrize("report_type", ["early_warning", "notification"])
def test_missing_deadline_is_not_mistaken_for_awaiting_fix(report_type):
    with pytest.raises(ValueError, match="must have a deadline"):
        unsubmitted_obligation_status(
            report_type=report_type, applicable=True, due_at=None, now=DUE
        )


@pytest.mark.parametrize("report_type", ["user_advisory", "unknown"])
def test_non_obligation_report_type_is_rejected(report_type):
    with pytest.raises(ValueError, match="unknown Article 14 report type"):
        unsubmitted_obligation_status(report_type=report_type, applicable=True, due_at=DUE, now=DUE)


@pytest.mark.parametrize("field", ["due_at", "now"])
def test_naive_datetimes_are_rejected(field):
    times = {"due_at": DUE, "now": DUE}
    times[field] = DUE.replace(tzinfo=None)

    with pytest.raises(ValueError, match="timezone-aware"):
        unsubmitted_obligation_status(report_type="early_warning", applicable=True, **times)


@pytest.mark.parametrize("report_type", REPORT_TYPES)
@pytest.mark.parametrize(
    "submitted_at,expected",
    [
        (DUE - timedelta(seconds=1), "submitted"),
        (DUE, "submitted"),
        (DUE + timedelta(seconds=1), "submitted_late"),
    ],
    ids=["one-second-before", "exactly-due", "one-second-after"],
)
def test_submitted_status_at_the_due_time_boundary(report_type, submitted_at, expected):
    assert (
        submitted_report_status(report_type=report_type, submitted_at=submitted_at, due_at=DUE)
        == expected
    )


def test_submitted_status_compares_whole_seconds_in_utc():
    # 04:00:00.9 at UTC-5 is 09:00:00 UTC once truncated to the second: on time.
    submitted_at = datetime(2026, 10, 6, 4, 0, 0, 900000, tzinfo=timezone(timedelta(hours=-5)))

    assert (
        submitted_report_status(report_type="early_warning", submitted_at=submitted_at, due_at=DUE)
        == "submitted"
    )


def test_a_deadline_moved_earlier_makes_a_recorded_report_late():
    # Q4 proposal: status uses the deadline from the ticket's current data.
    inputs = {"report_type": "notification", "submitted_at": DUE}

    assert submitted_report_status(**inputs, due_at=DUE) == "submitted"
    assert submitted_report_status(**inputs, due_at=DUE - timedelta(seconds=1)) == "submitted_late"


def test_a_final_report_with_no_deadline_counts_as_on_time():
    assert (
        submitted_report_status(report_type="final_report", submitted_at=DUE, due_at=None)
        == "submitted"
    )


@pytest.mark.parametrize("report_type", ["early_warning", "notification"])
def test_a_recorded_report_other_than_the_final_report_needs_a_deadline(report_type):
    with pytest.raises(ValueError):
        submitted_report_status(report_type=report_type, submitted_at=DUE, due_at=None)


def test_submitted_status_rejects_unknown_report_types():
    with pytest.raises(ValueError):
        submitted_report_status(report_type="user_advisory", submitted_at=DUE, due_at=DUE)
