"""Ticket HTTP operations, using the pure domain helpers and shared platform."""

from copy import deepcopy
from uuid import UUID

from django.db.models import Max
from ninja import Router
from ninja.responses import Status

from core import clock
from core.domain.deadlines import calculate_deadlines
from core.domain.statuses import unsubmitted_obligation_status
from core.domain.triage import triage_ticket
from core.models import AuditEntry, Ticket
from core.schemas import TicketCreate, TicketUpdate, TriageRequest
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


def _render(ticket: Ticket, now, *, detail: bool = False) -> dict:
    applicable = ticket.aware_at is not None and ticket.resolution not in (
        "invalid",
        "not_actively_exploited",
    )
    due_times = {"early_warning": None, "notification": None, "final_report": None}
    if applicable:
        deadline_field = "aware_at"
        try:
            fix_time = _fix_time(ticket.data)
            if fix_time is not None and fix_time > ticket.aware_at:
                deadline_field = "fix.available_at"
            deadlines = calculate_deadlines(ticket.aware_at, fix_time)
        except (OverflowError, ValueError):
            raise RuleViolation(
                [field_error(deadline_field, "reporting deadlines are out of range")]
            ) from None
        due_times = {
            "early_warning": deadlines.early_warning_due,
            "notification": deadlines.notification_due,
            "final_report": deadlines.final_report_due,
        }
    obligations = {
        report_type: {
            "status": unsubmitted_obligation_status(
                report_type=report_type, applicable=applicable, due_at=due_at, now=now
            ),
            "due_at": format_timestamp(due_at) if due_at is not None else None,
            "submitted_at": None,
            "reference": None,
        }
        for report_type, due_at in due_times.items()
    }
    deadlines = [value for value in due_times.values() if value is not None]
    result = {key: deepcopy(ticket.data.get(key)) for key in CLIENT_FIELDS}
    result["product"]["affected_versions"] = result["product"].get("affected_versions") or []
    result["member_states"] = result["member_states"] or []
    if result["fix"] is not None:
        result["fix"]["fixed_versions"] = result["fix"].get("fixed_versions") or []
    result.update(
        id=str(ticket.pk),
        state=ticket.state,
        resolution=ticket.resolution,
        received_at=format_timestamp(ticket.received_at),
        aware_at=format_timestamp(ticket.aware_at) if ticket.aware_at is not None else None,
        obligations=obligations,
        next_due_at=format_timestamp(min(deadlines)) if deadlines else None,
    )
    if detail:
        reporter = deepcopy(ticket.data.get("reporter"))
        result["reporter"] = (
            {"name": reporter.get("name"), "contact": reporter.get("contact")}
            if reporter is not None
            else None
        )
    return result


def _snapshot(ticket: Ticket) -> dict:
    return {
        **deepcopy(ticket.data),
        "id": str(ticket.pk),
        "state": ticket.state,
        "resolution": ticket.resolution,
        "received_at": format_timestamp(ticket.received_at),
        "aware_at": format_timestamp(ticket.aware_at) if ticket.aware_at is not None else None,
    }


def _changes(before: dict, after: dict, prefix: str = "") -> list[dict]:
    changes = []
    for key in sorted(before.keys() | after.keys()):
        if key == "reporter" and not prefix:
            continue
        old, new = before.get(key), after.get(key)
        field = f"{prefix}.{key}" if prefix else key
        if isinstance(old, dict) and isinstance(new, dict):
            changes.extend(_changes(old, new, field))
        elif old != new:
            changes.append({"field": field, "old": old, "new": new})
    return changes


def _audit(ticket: Ticket, *, now, actor: str, action: str, before: dict, reason=None):
    seq = (ticket.audit_entries.aggregate(last=Max("seq"))["last"] or 0) + 1
    AuditEntry.objects.create(
        ticket=ticket,
        seq=seq,
        at=now,
        actor=actor,
        action=action,
        changes=_changes(before, _snapshot(ticket)),
        reason=reason,
    )


@router.post("", response={201: dict}, operation_id="submitTicket")
def create_ticket(request):
    actor = require_actor(request)
    payload = parse_body(request, TicketCreate)
    now = clock.now()
    ticket = Ticket.objects.create(
        received_at=now, data=payload.model_dump(mode="json", exclude_unset=True)
    )
    _audit(ticket, now=now, actor=actor, action="created", before={})
    return Status(201, _render(ticket, now))


@router.get("", response=list[dict], operation_id="listTickets")
def list_tickets(request):
    now = clock.now()
    tickets = [_render(ticket, now) for ticket in Ticket.objects.all()]
    return sorted(
        tickets,
        key=lambda ticket: (
            ticket["next_due_at"] is None,
            ticket["next_due_at"] or "",
            ticket["id"],
        ),
    )


@router.get("/{id}", response=dict, operation_id="getTicket")
def get_ticket(request, id: str):
    ticket = _ticket(id)
    return _render(ticket, clock.now(), detail=True)


@router.post("/{id}/triage", response=dict, operation_id="triageTicket")
def triage(request, id: str):
    ticket = _ticket(id, lock=True)
    actor = require_actor(request)
    payload = parse_body(request, TriageRequest)
    now = clock.now()
    result = triage_ticket(
        state=ticket.state, decision=payload.decision, now=now, aware_at=payload.aware_at
    )
    before = _snapshot(ticket)
    ticket.state, ticket.resolution, ticket.aware_at = (
        result.state,
        result.resolution,
        result.aware_at,
    )
    response = _render(ticket, now)
    ticket.save(update_fields=["state", "resolution", "aware_at"])
    _audit(ticket, now=now, actor=actor, action="triaged", before=before, reason=payload.reason)
    return response


@router.patch("/{id}", response=dict, operation_id="updateTicket")
def update_ticket(request, id: str):
    ticket = _ticket(id, lock=True)
    actor = require_actor(request)
    payload = parse_body(request, TicketUpdate)
    if ticket.state == "closed":
        raise Conflict("A closed ticket cannot be changed.")
    if "aware_at" in payload.model_fields_set and ticket.state != "reportable":
        raise Conflict("Awareness can only be changed on a reportable ticket.")
    now = clock.now()
    errors = []
    if "aware_at" in payload.model_fields_set:
        if payload.change_reason is None:
            errors.append(field_error("change_reason", "required when changing aware_at"))
        if payload.aware_at > now:
            errors.append(field_error("aware_at", "must not be later than now"))
    before = _snapshot(ticket)
    data = deepcopy(ticket.data)
    for key, value in payload.model_dump(mode="json", exclude_unset=True).items():
        if key in ("aware_at", "change_reason"):
            continue
        if isinstance(value, dict) and isinstance(data.get(key), dict):
            data[key] = {**data[key], **value}
        else:
            data[key] = value
    fix_time = _fix_time(data)
    if fix_time is not None and fix_time > now:
        errors.append(field_error("fix.available_at", "must not be later than now"))
    if errors:
        raise RuleViolation(errors)
    ticket.data = data
    if "aware_at" in payload.model_fields_set:
        ticket.aware_at = payload.aware_at
    response = _render(ticket, now)
    ticket.save(update_fields=["data", "aware_at"])
    _audit(
        ticket, now=now, actor=actor, action="updated", before=before, reason=payload.change_reason
    )
    return response


@router.get("/{id}/audit", response=list[dict], operation_id="getAuditLog")
def get_audit(request, id: str):
    ticket = _ticket(id)
    return [
        {
            "seq": entry.seq,
            "at": format_timestamp(entry.at),
            "actor": entry.actor,
            "action": entry.action,
            "changes": entry.changes,
            "reason": entry.reason,
        }
        for entry in ticket.audit_entries.all()
    ]
