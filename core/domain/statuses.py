"""Submission statuses for Phase 4."""

from datetime import datetime
from typing import Literal

from cra_service.timestamps import to_utc_second

ReportType = Literal["early_warning", "notification", "final_report"]
SubmittedStatus = Literal["submitted", "submitted_late"]


def submitted_report_status(
    *,
    report_type: ReportType,
    submitted_at: datetime | None,
    due_at: datetime | None,
) -> SubmittedStatus | None:
    """Return the submitted status for a locking report snapshot.

    Rule from the handoff:
    - submitted if submitted_at <= due_at
    - submitted_late otherwise
    - handle the E6 boundary and a clock moved backward
    """
    if report_type not in ("early_warning", "notification", "final_report"):
        raise ValueError("unknown Article 14 report type")
    if submitted_at is None:
        return None

    submitted_at = to_utc_second(submitted_at)
    due_at = to_utc_second(due_at) if due_at is not None else None

    if due_at is None:
        return "submitted"

    return "submitted" if submitted_at <= due_at else "submitted_late"