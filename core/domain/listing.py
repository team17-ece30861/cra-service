"""Listing helpers (REQ-10; AC-11): the next unmet deadline and the urgency order."""

from collections.abc import Collection, Mapping
from datetime import datetime

from core.domain.statuses import ReportType
from cra_service.timestamps import to_utc_second


def next_due_at(
    *,
    applicable: bool,
    due_times: Mapping[ReportType, datetime | None],
    submitted: Collection[ReportType],
) -> datetime | None:
    """The earliest due time among applicable reports not yet recorded; None if none.

    A final report waiting for a fix time has no deadline, so it doesn't count.
    An overdue report still counts: its deadline is unmet.
    """
    if not applicable:
        return None
    unmet = [
        to_utc_second(due_at)
        for report_type, due_at in due_times.items()
        if due_at is not None and report_type not in submitted
    ]
    return min(unmet) if unmet else None


def urgency_key(*, next_due_at: datetime | None, received_at: datetime, ticket_id: str) -> tuple:
    """Sort key for the ticket list: nearest unmet deadline first, tickets with none last.

    Ties (same deadline, or both none) go to the ticket received first, then the ID
    (Q2, agreed with Team 21 on 2026-11-01; the ID makes the order total).
    """
    received_at = to_utc_second(received_at)
    if next_due_at is None:
        return (1, received_at, received_at, ticket_id)
    return (0, to_utc_second(next_due_at), received_at, ticket_id)
