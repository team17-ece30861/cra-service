"""Supplemental checks for the submitted-status helper merged in PR #76."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from core.domain.statuses import submitted_report_status

DUE = datetime(2026, 10, 6, 9, tzinfo=UTC)
REPORT_TYPES = ("early_warning", "notification", "final_report")


@pytest.mark.parametrize("report_type", REPORT_TYPES)
@pytest.mark.parametrize(
    "seconds,status", [(-1, "submitted"), (0, "submitted"), (1, "submitted_late")]
)
def test_submission_boundary_is_inclusive_for_each_report(report_type, seconds, status):
    assert (
        submitted_report_status(
            report_type=report_type, submitted_at=DUE + timedelta(seconds=seconds), due_at=DUE
        )
        == status
    )


@pytest.mark.parametrize("report_type", ["early_warning", "notification"])
def test_recorded_early_warning_and_notification_require_a_deadline(report_type):
    with pytest.raises(ValueError, match="must have a deadline"):
        submitted_report_status(report_type=report_type, submitted_at=DUE, due_at=None)


def test_offset_and_fractions_are_normalized_before_comparison():
    submitted = DUE.astimezone(timezone(timedelta(hours=2))).replace(microsecond=999_999)
    assert (
        submitted_report_status(
            report_type="notification", submitted_at=submitted, due_at=DUE.replace(microsecond=1)
        )
        == "submitted"
    )


def test_published_helper_treats_recorded_final_report_without_current_deadline_as_submitted():
    assert (
        submitted_report_status(report_type="final_report", submitted_at=DUE, due_at=None)
        == "submitted"
    )


@pytest.mark.parametrize("field", ["submitted_at", "due_at"])
def test_naive_times_are_internal_integration_errors(field):
    times = {"submitted_at": DUE, "due_at": DUE}
    times[field] = DUE.replace(tzinfo=None)
    with pytest.raises(ValueError, match="timezone-aware"):
        submitted_report_status(report_type="early_warning", **times)


@pytest.mark.parametrize("report_type", ["user_advisory", "unknown"])
def test_unknown_regulatory_types_remain_internal_integration_errors(report_type):
    with pytest.raises(ValueError, match="unknown Article 14"):
        submitted_report_status(report_type=report_type, submitted_at=DUE, due_at=DUE)
