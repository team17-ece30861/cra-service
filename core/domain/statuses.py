"""Obligation statuses (REQ-03/REQ-05/REQ-08; Model B)."""

from datetime import datetime
from typing import Literal

from cra_service.timestamps import to_utc_second

ReportType = Literal["early_warning", "notification", "final_report"]
UnsubmittedStatus = Literal["not_applicable", "awaiting_fix", "pending", "overdue"]
SubmittedStatus = Literal["submitted", "submitted_late"]


def unsubmitted_obligation_status(
    *,
    report_type: ReportType,
    applicable: bool,
    due_at: datetime | None,
    now: datetime,
) -> UnsubmittedStatus:
    """Derive an unsubmitted report's status without reading or changing data.

    The caller determines applicability and supplies core.clock.now() and a
    calculated deadline. Only an applicable final report may have no deadline.
    Submitted reports use submitted_report_status instead.
    """
    if report_type not in ("early_warning", "notification", "final_report"):
        raise ValueError("unknown Article 14 report type")
    if not applicable:
        return "not_applicable"
    if due_at is None:
        if report_type == "final_report":
            return "awaiting_fix"
        raise ValueError("an applicable early warning or notification must have a deadline")

    due_at = to_utc_second(due_at)
    now = to_utc_second(now)
    return "overdue" if now > due_at else "pending"


def submitted_report_status(
    *,
    report_type: ReportType,
    submitted_at: datetime,
    due_at: datetime | None,
) -> SubmittedStatus:
    """Derive a recorded report's status: submitted if submitted_at <= due_at,
    otherwise submitted_late (Model D E6 boundary: exactly at the deadline is on time).

    The caller passes the deadline calculated from the ticket's current data, so a
    later edit that moves the deadline earlier can make a report late (Q4 proposal).
    A final report with no deadline (its fix time was cleared) counts as on time; a
    missing early-warning or notification deadline is an integration error. Takes no
    clock, so moving the clock never changes a recorded report's status.
    """
    if report_type not in ("early_warning", "notification", "final_report"):
        raise ValueError("unknown Article 14 report type")
    submitted_at = to_utc_second(submitted_at)
    if due_at is None:
        if report_type == "final_report":
            return "submitted"
        raise ValueError("a recorded early warning or notification must have a deadline")
    return "submitted" if submitted_at <= to_utc_second(due_at) else "submitted_late"
