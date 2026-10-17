"""Elapsed-time reporting deadlines (REQ-04; UTC normalization: AC-14)."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from cra_service.timestamps import to_utc_second


@dataclass(frozen=True)
class Deadlines:
    early_warning_due: datetime
    notification_due: datetime
    final_report_due: datetime | None


def calculate_deadlines(aware_at: datetime, fix_available_at: datetime | None = None) -> Deadlines:
    """Calculate deadlines for an actively exploited vulnerability.

    Inputs are timezone-aware datetimes; outputs are UTC to the second. Before
    a fix is available, there is no final-report deadline. If the fix predates
    awareness, the final-report clock starts at awareness instead.

    The caller validates ticket state and future timestamps. This function
    reads no clock, changes no data, and performs no persistence.
    """
    aware_at = to_utc_second(aware_at)
    final_report_due = None
    if fix_available_at is not None:
        fix_available_at = to_utc_second(fix_available_at)
        final_report_due = max(aware_at, fix_available_at) + timedelta(days=14)

    return Deadlines(
        early_warning_due=aware_at + timedelta(hours=24),
        notification_due=aware_at + timedelta(hours=72),
        final_report_due=final_report_due,
    )
