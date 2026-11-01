"""Ticket HTTP operations, using the pure domain helpers and shared platform."""

from copy import deepcopy
from uuid import UUID

from django.db.models import Max
from ninja import Router
from ninja.responses import Status

from core import clock
from core.domain.statuses import submitted_report_status, unsubmitted_obligation_status
from core.models import AuditEntry, ReportSubmission, Ticket
from cra_service.errors import Conflict, NotFound, RuleViolation, field_error
from cra_service.timestamps import format_timestamp, parse_timestamp
from cra_service.validation import parse_body, require_actor

router = Router(tags=["tickets"])
CLIENT_FIELDS = (
    "source",
    "title",
    "description",
    "product",
    "member_states",
    "vulnerability",
    "exploit",
    "mitigations",
    "impact",
    "malicious_actor",
    "sensitivity",
    "severity",
    "fix",
)

VALID_STATES = {"received", "reportable", "closed"}
VALID_OBLIGATION_STATUSES = {
    "not_applicable",
    "awaiting_fix",
    "pending",
    "overdue",
    "submitted",
    "submitted_late",
}


def _ticket(id: str, *, lock: bool = False) -> Ticket:
    try:
        key = UUID(id)
    except ValueError:
        raise NotFound() from None
    query = Ticket.objects.select_for_update() if lock else Ticket.objects
    try:
        return query.get(pk=key)
    except Ticket.DoesNotExist:
        raise NotFound() from None


def _fix_time(data: dict):
    value = (data.get("fix") or {}).get("available_at")
    return parse_timestamp(value) if value is not None else None
