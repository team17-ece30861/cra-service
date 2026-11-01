"""Ticket HTTP operations, using the pure domain helpers and shared platform."""

from copy import deepcopy
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import Max
from ninja import Router
from ninja.responses import Status

from core import clock
from core.domain.closure import close_ticket
from core.domain.deadlines import calculate_deadlines
from core.domain.drafts import DraftReportType, DraftResult, build_draft
from core.domain.listing import next_due_at, urgency_key
from core.domain.statuses import ReportType, submitted_report_status, unsubmitted_obligation_status
from core.domain.submissions import validate_submission
from core.domain.triage import triage_ticket
from core.models import AuditEntry, ReportSubmission, Ticket
from core.schemas import (
    ObligationStatus,
    SubmissionRequest,
    TicketCreate,
    TicketState,
    TicketUpdate,
    TriageRequest,
)
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


def _obligation(report_type, due_at, submission, applicable: bool, now) -> dict:
    """One report's obligation: a recorded report's status is checked against the
    current deadline (Q4), so an edit that moves the deadline earlier can make it late."""
    if submission is None:
        status = unsubmitted_obligation_status(
            report_type=report_type, applicable=applicable, due_at=due_at, now=now
        )
    else:
        status = submitted_report_status(
            report_type=report_type, submitted_at=submission.submitted_at, due_at=due_at
        )
    return {
        "status": status,
        "due_at": format_timestamp(due_at) if due_at is not None else None,
        "submitted_at": format_timestamp(submission.submitted_at) if submission else None,
        "reference": submission.reference if submission else None,
    }


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
    submissions = {s.report_type: s for s in ticket.submissions.all()}
    obligations = {
        report_type: _obligation(report_type, due_at, submissions.get(report_type), applicable, now)
        for report_type, due_at in due_times.items()
    }
    next_due = next_due_at(applicable=applicable, due_times=due_times, submitted=submissions)
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
        next_due_at=format_timestamp(next_due) if next_due is not None else None,
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


def _audit(ticket: Ticket, *, now, actor: str, action: str, before: dict, reason=None, after=None):
    seq = (ticket.audit_entries.aggregate(last=Max("seq"))["last"] or 0) + 1
    AuditEntry.objects.create(
        ticket=ticket,
        seq=seq,
        at=now,
        actor=actor,
        action=action,
        changes=_changes(before, _snapshot(ticket) if after is None else after),
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
def list_tickets(
    request,
    state: TicketState | None = None,
    obligation_status: ObligationStatus | None = None,
):
    now = clock.now()
    tickets = Ticket.objects.prefetch_related("submissions")
    if state is not None:
        tickets = tickets.filter(state=state)
    rows = []
    for ticket in tickets:
        rendered = _render(ticket, now)
        if obligation_status is not None and not any(
            obligation["status"] == obligation_status
            for obligation in rendered["obligations"].values()
        ):
            continue
        next_due = rendered["next_due_at"]
        key = urgency_key(
            next_due_at=parse_timestamp(next_due) if next_due is not None else None,
            received_at=ticket.received_at,
            ticket_id=rendered["id"],
        )
        rows.append((key, rendered))
    rows.sort(key=lambda row: row[0])
    return [rendered for _, rendered in rows]


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
    before_view = _render(ticket, now, detail=True)
    data = deepcopy(ticket.data)
    for key, value in payload.model_dump(mode="json", exclude_unset=True).items():
        if key in ("aware_at", "change_reason"):
            continue
        if isinstance(value, dict) and isinstance(data.get(key), dict):
            data[key] = {**data[key], **value}
        else:
            data[key] = value
    # Only a fix time this request sends is checked. A stored one may be later than now
    # (accepted at intake, or the test clock moved back) and must not block other edits.
    if payload.fix is not None and "available_at" in payload.fix.model_fields_set:
        if payload.fix.available_at > now:
            errors.append(field_error("fix.available_at", "must not be later than now"))
    if errors:
        raise RuleViolation(errors)
    ticket.data = data
    if "aware_at" in payload.model_fields_set:
        ticket.aware_at = payload.aware_at
    response = _render(ticket, now)
    # Q6 (agreed with Team 21, 2026-11-01): a PATCH that changes nothing succeeds but adds
    # no audit entry and saves nothing. "Nothing" means every read looks the same, so it's
    # judged on the full single-ticket view: null or [] for a field never set is no change,
    # and a reporter-only edit is a change (its entry leaves the reporter out).
    if _render(ticket, now, detail=True) == before_view:
        return response
    ticket.save(update_fields=["data", "aware_at"])
    _audit(
        ticket, now=now, actor=actor, action="updated", before=before, reason=payload.change_reason
    )
    return response


@router.post("/{id}/close", response=dict, operation_id="closeTicket")
def close(request, id: str):
    ticket = _ticket(id, lock=True)
    actor = require_actor(request)
    result = close_ticket(
        state=ticket.state,
        submitted_reports=set(ticket.submissions.values_list("report_type", flat=True)),
    )
    now = clock.now()
    before = _snapshot(ticket)
    ticket.state, ticket.resolution = result.state, result.resolution
    ticket.save(update_fields=["state", "resolution"])
    _audit(ticket, now=now, actor=actor, action="closed", before=before)
    return _render(ticket, now)


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


def _render_draft(ticket: Ticket, type: DraftReportType, now) -> dict:
    submission = (
        ticket.submissions.filter(report_type=type).first() if type != "user_advisory" else None
    )
    if submission is None:
        draft = build_draft(
            report_type=type,
            ticket_id=str(ticket.pk),
            aware_at=ticket.aware_at,
            ticket_fields=ticket.data,
        )
        content, missing_fields = draft.content, draft.missing_fields
    else:
        content, missing_fields = deepcopy(submission.content), []

    # The ticket's obligation is the single source for status, deadline and receipt
    # details, so a draft and its ticket can never disagree.
    obligation = {"status": None, "due_at": None, "submitted_at": None, "reference": None}
    if type != "user_advisory":
        obligation = _render(ticket, now)["obligations"][type]

    return {
        "ticket_id": str(ticket.pk),
        "type": type,
        **obligation,
        "content": content,
        "missing_fields": missing_fields,
    }


@router.get("/{id}/reports/{type}", response=dict, operation_id="getDraft")
def get_draft(request, id: str, type: DraftReportType):
    ticket = _ticket(id)
    if ticket.aware_at is None or not (
        ticket.state == "reportable"
        or (ticket.state == "closed" and ticket.resolution == "resolved")
    ):
        raise Conflict("Drafts are only available for tickets that became reportable.")
    return _render_draft(ticket, type, clock.now())


@router.post("/{id}/reports/{type}/submission", response=dict, operation_id="recordSubmission")
def record_submission(request, id: str, type: ReportType):
    ticket = _ticket(id, lock=True)
    actor = require_actor(request)
    payload = parse_body(request, SubmissionRequest, required=False)
    now = clock.now()
    submitted_reports = set(ticket.submissions.values_list("report_type", flat=True))
    draft = DraftResult(content={}, missing_fields=[])
    if ticket.aware_at is not None:
        draft = build_draft(
            report_type=type,
            ticket_id=str(ticket.pk),
            aware_at=ticket.aware_at,
            ticket_fields=ticket.data,
        )
    submitted_at = validate_submission(
        state=ticket.state,
        report_type=type,
        aware_at=ticket.aware_at,
        now=now,
        submitted_reports=submitted_reports,
        missing_fields=draft.missing_fields,
        submitted_at=payload.submitted_at,
    )
    try:
        with transaction.atomic():
            ReportSubmission.objects.create(
                ticket=ticket,
                report_type=type,
                submitted_at=submitted_at,
                reference=payload.reference,
                content=draft.content,
                actor=actor,
            )
    except IntegrityError:
        if ticket.submissions.filter(report_type=type).exists():
            raise Conflict("This report has already been submitted.") from None
        raise
    _audit(
        ticket,
        now=now,
        actor=actor,
        action="report_submitted",
        before={"reports": {}},
        after={
            "reports": {
                type: {
                    "submitted_at": format_timestamp(submitted_at),
                    "reference": payload.reference,
                    "content": draft.content,
                    "actor": actor,
                }
            }
        },
    )
    return _render_draft(ticket, type, now)
