"""Ticket triage transitions (REQ-02, REQ-03; AC-04 and AC-05)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from cra_service.errors import BadRequest, Conflict, RuleViolation, field_error
from cra_service.timestamps import to_utc_second

TriageDecision = Literal["actively_exploited", "not_actively_exploited", "invalid"]


@dataclass(frozen=True)
class TriageResult:
    state: Literal["reportable", "closed"]
    resolution: Literal["not_actively_exploited", "invalid"] | None
    aware_at: datetime | None


def triage_ticket(
    *,
    state: str,
    decision: TriageDecision,
    now: datetime,
    aware_at: datetime | None = None,
) -> TriageResult:
    """Return triage changes without mutating a ticket or reading the clock.

    The caller validates the request (including its required reason), checks
    authentication and resource existence, and supplies core.clock.now().
    Datetimes must be timezone-aware and are normalized to UTC seconds.
    """
    if decision not in ("actively_exploited", "not_actively_exploited", "invalid"):
        raise BadRequest(
            [
                field_error(
                    "decision", "must be one of actively_exploited, not_actively_exploited, invalid"
                )
            ]
        )
    if decision == "actively_exploited" and aware_at is None:
        raise BadRequest([field_error("aware_at", "required when decision is actively_exploited")])
    if state != "received":
        raise Conflict("Only a received ticket can be triaged.")

    if decision == "actively_exploited":
        aware_at = to_utc_second(aware_at)
        if aware_at > to_utc_second(now):
            raise RuleViolation([field_error("aware_at", "must not be later than now")])
        return TriageResult(state="reportable", resolution=None, aware_at=aware_at)

    return TriageResult(state="closed", resolution=decision, aware_at=None)
