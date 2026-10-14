"""REQ-04 deadline math and AC-14 timestamp normalization, without a database."""

from datetime import UTC, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from core.domain.deadlines import Deadlines, calculate_deadlines


def utc(*args) -> datetime:
    return datetime(*args, tzinfo=UTC)


def test_awareness_starts_early_warning_and_notification_deadlines():
    deadlines = calculate_deadlines(utc(2026, 10, 7, 14, 30, 0))

    assert deadlines == Deadlines(
        early_warning_due=utc(2026, 10, 8, 14, 30, 0),
        notification_due=utc(2026, 10, 10, 14, 30, 0),
        final_report_due=None,
    )


@pytest.mark.parametrize(
    "fix_available_at,expected",
    [
        (utc(2026, 10, 9, 8, 15, 0), utc(2026, 10, 23, 8, 15, 0)),
        (utc(2026, 10, 7, 14, 30, 0), utc(2026, 10, 21, 14, 30, 0)),
        (utc(2026, 10, 1, 9, 0, 0), utc(2026, 10, 21, 14, 30, 0)),
    ],
    ids=["fix-after-awareness", "fix-at-awareness", "fix-before-awareness"],
)
def test_final_report_is_due_fourteen_days_after_later_of_awareness_and_fix(
    fix_available_at, expected
):
    deadlines = calculate_deadlines(utc(2026, 10, 7, 14, 30, 0), fix_available_at)

    assert deadlines.final_report_due == expected
    assert deadlines.early_warning_due == utc(2026, 10, 8, 14, 30, 0)
    assert deadlines.notification_due == utc(2026, 10, 10, 14, 30, 0)


def test_offsets_are_normalized_before_comparing_awareness_and_fix():
    aware_at = datetime(2026, 10, 7, 16, 30, 0, tzinfo=timezone(timedelta(hours=2)))
    fix_available_at = datetime(2026, 10, 7, 10, 0, 0, tzinfo=timezone(timedelta(hours=-5)))

    deadlines = calculate_deadlines(aware_at, fix_available_at)

    assert deadlines == Deadlines(
        early_warning_due=utc(2026, 10, 8, 14, 30, 0),
        notification_due=utc(2026, 10, 10, 14, 30, 0),
        final_report_due=utc(2026, 10, 21, 15, 0, 0),
    )
    assert deadlines.early_warning_due.tzinfo is UTC
    assert deadlines.notification_due.tzinfo is UTC
    assert deadlines.final_report_due.tzinfo is UTC


def test_fractional_seconds_are_truncated_instead_of_rounded():
    deadlines = calculate_deadlines(
        utc(2026, 10, 7, 14, 30, 59, 999_999), utc(2026, 10, 8, 9, 0, 59, 999_999)
    )

    assert deadlines == Deadlines(
        early_warning_due=utc(2026, 10, 8, 14, 30, 59),
        notification_due=utc(2026, 10, 10, 14, 30, 59),
        final_report_due=utc(2026, 10, 22, 9, 0, 59),
    )


@pytest.mark.parametrize(
    "aware_at,early_warning_due,notification_due,final_report_due",
    [
        (
            utc(2026, 12, 31, 23, 59, 59),
            utc(2027, 1, 1, 23, 59, 59),
            utc(2027, 1, 3, 23, 59, 59),
            utc(2027, 1, 14, 23, 59, 59),
        ),
        (
            utc(2028, 2, 28, 12, 0, 0),
            utc(2028, 2, 29, 12, 0, 0),
            utc(2028, 3, 2, 12, 0, 0),
            utc(2028, 3, 13, 12, 0, 0),
        ),
    ],
    ids=["year-boundary", "leap-day"],
)
def test_deadlines_cross_calendar_boundaries(
    aware_at, early_warning_due, notification_due, final_report_due
):
    assert calculate_deadlines(aware_at, aware_at) == Deadlines(
        early_warning_due, notification_due, final_report_due
    )


@pytest.mark.parametrize(
    "aware_at,expected_early_warning,expected_notification,expected_final",
    [
        (
            datetime(2026, 3, 7, 12, tzinfo=ZoneInfo("America/New_York")),
            utc(2026, 3, 8, 17),
            utc(2026, 3, 10, 17),
            utc(2026, 3, 21, 17),
        ),
        (
            datetime(2026, 10, 31, 12, tzinfo=ZoneInfo("America/New_York")),
            utc(2026, 11, 1, 16),
            utc(2026, 11, 3, 16),
            utc(2026, 11, 14, 16),
        ),
    ],
    ids=["spring-forward", "fall-back"],
)
def test_daylight_saving_does_not_change_elapsed_time(
    aware_at, expected_early_warning, expected_notification, expected_final
):
    assert calculate_deadlines(aware_at, aware_at) == Deadlines(
        expected_early_warning, expected_notification, expected_final
    )


@pytest.mark.parametrize("field", ["aware_at", "fix_available_at"])
def test_naive_datetimes_are_rejected(field):
    inputs = {
        "aware_at": utc(2026, 10, 7, 14, 30, 0),
        "fix_available_at": utc(2026, 10, 9, 8, 15, 0),
    }
    inputs[field] = inputs[field].replace(tzinfo=None)

    with pytest.raises(ValueError, match="timezone-aware"):
        calculate_deadlines(**inputs)


def test_changed_inputs_recalculate_deadlines_without_changing_previous_result():
    original = calculate_deadlines(utc(2026, 10, 7, 14, 30, 0))
    changed_awareness = calculate_deadlines(utc(2026, 10, 8, 9, 0, 0))
    changed_fix = calculate_deadlines(utc(2026, 10, 8, 9, 0, 0), utc(2026, 10, 10, 12, 0, 0))

    assert changed_awareness == Deadlines(
        utc(2026, 10, 9, 9, 0, 0), utc(2026, 10, 11, 9, 0, 0), None
    )
    assert changed_fix == Deadlines(
        utc(2026, 10, 9, 9, 0, 0), utc(2026, 10, 11, 9, 0, 0), utc(2026, 10, 24, 12, 0, 0)
    )
    assert original == Deadlines(utc(2026, 10, 8, 14, 30, 0), utc(2026, 10, 10, 14, 30, 0), None)
