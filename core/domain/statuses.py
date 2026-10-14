"""Initial obligation statuses for Phase 3 (REQ-03/REQ-05; Model B)."""

from datetime import datetime
from typing import Literal

from cra_service.timestamps import to_utc_second

ReportType = Literal["early_warning", "notification", "final_report"]
UnsubmittedStatus = Literal["not_applicable", "awaiting_fix", "pending", "overdue"]


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
    Submitted reports must use the later Phase 4 submission-status logic.
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
