"""Pure reportable-ticket closure rule (REQ-09; AC-10)."""

from collections.abc import Collection
from dataclasses import dataclass
from typing import Literal

from core.domain.statuses import ReportType
from cra_service.errors import Conflict

REQUIRED_REPORTS = frozenset({"early_warning", "notification", "final_report"})


@dataclass(frozen=True)
class ClosureResult:
    state: Literal["closed"]
    resolution: Literal["resolved"]


def close_ticket(*, state: str, submitted_reports: Collection[ReportType]) -> ClosureResult:
    """Return closure changes; the caller persists and audits them atomically."""
    if state != "reportable":
        raise Conflict("Only a reportable ticket can be resolved.")
    if not REQUIRED_REPORTS.issubset(submitted_reports):
        raise Conflict("All three reports must be submitted before closing the ticket.")
    return ClosureResult(state="closed", resolution="resolved")
