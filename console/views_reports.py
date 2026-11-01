"""Report pages (4.U3): the Report Draft page, the Record Submission sheet and the Close
Ticket dialog. Each sheet has its own address, so it can be bookmarked or reloaded: the GET
renders the page it belongs to with the sheet open, and ledger's reports.js opens and closes
it in place when it's clicked from that page. A POST makes exactly one change through the
API, as the signed-in person; a failure re-renders the sheet with the API's errors."""

from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from console import present
from console import present_reports as rp
from console.api_calls import call_api
from console.flash import flash
from console.views import _shell, signed_in_required, ticket_context
from core import clock


def _not_found(request, now):
    everything = call_api(request, "GET", "/tickets")
    context = _shell(request, "ticket", everything.data if everything.ok else [], now)
    return render(request, "console/not_found.html", context, status=404)


def _report_context(request, ticket_id: str, kind: str, now) -> dict | None:
    """The Report Draft page for one report type, or None when there's no such ticket or
    type. A ticket that never became reportable has no drafts (the API's 409): the page
    says so instead of showing one."""
    if kind not in rp.REPORT_TYPES:
        return None
    found = call_api(request, "GET", f"/tickets/{ticket_id}")
    if found.status == 404:
        return None
    t = found.data
    draft = call_api(request, "GET", f"/tickets/{ticket_id}/reports/{kind}")
    if draft.status == 404:
        return None
    everything = call_api(request, "GET", "/tickets")
    # Only what the report pages show: the reporter stays on the ticket page.
    ticket = {"id": t["id"], "title": t["title"], "state": t["state"]}
    return {
        **_shell(request, "report", everything.data if everything.ok else [], now),
        "ticket": ticket,
        "kind": kind,
        "tabs": rp.tabs(ticket_id, kind),
        "d": rp.draft_view(draft.data, now) if draft.ok else None,
        "no_draft": (draft.data or {}).get("detail") if not draft.ok else "",
        "kind_label": rp.LABEL[kind],
        "kind_title": rp.TITLE[kind],
    }


@never_cache
@signed_in_required
@require_http_methods(["GET", "HEAD"])
def report(request, ticket_id: str, kind: str):
    now = clock.now()
    context = _report_context(request, ticket_id, kind, now)
    if context is None:
        return _not_found(request, now)
    if context["d"] and context["d"]["recordable"]:
        # Ready to open in place from Record Submission.
        context["rs"] = _record_sheet(context, ticket_id, kind, False, now)
    return render(request, "console/report.html", context)


def _record_sheet(context: dict, ticket_id: str, kind: str, from_ticket: bool, now) -> dict:
    """The Record Submission sheet over the page it was opened from."""
    d = context.get("d") or {}
    if from_ticket:
        base = reverse("console:ticket", args=[ticket_id])
    else:
        base = reverse("console:report", args=[ticket_id, kind])
    return {
        "type": kind,
        "label": rp.LABEL[kind],
        "title": rp.TITLE[kind],
        "ticket_title": context["ticket"]["title"],
        "due": d.get("due"),
        "due_at": d.get("due_at") or "",
        "aware": d.get("aware"),
        "aware_at": d.get("aware_at") or "",
        "badge": d.get("badge"),
        "awaiting_fix": d.get("awaiting_fix"),
        "locked": d.get("locked"),
        "submitted": d.get("submitted"),
        "missing": [r["label"] for r in d.get("missing", [])],
        "missing_first": (d.get("missing") or [{}])[0].get("path"),
        "no_draft": context.get("no_draft"),
        "action": reverse("console:record", args=[ticket_id, kind]),
        "base": base,
        "done": reverse("console:ticket", args=[ticket_id]),
        # Edit Ticket arrives with PR 2 (4.U2): /console/tickets/<id>/edit?focus=<field>
        "edit": reverse("console:ticket", args=[ticket_id]) + "/edit",
        "from_ticket": from_ticket,
        "now": rp.ui_time(present.iso(now)),
        "values": {"submitted_at": rp.ui_time(present.iso(now)), "reference": ""},
        "errors": {},
        "problem": "",
    }


@never_cache
@signed_in_required
@require_http_methods(["GET", "HEAD", "POST"])
def record(request, ticket_id: str, kind: str):
    now = clock.now()
    if kind == "user_advisory":
        return _not_found(request, now)  # nothing to record: the API's 404 too
    from_ticket = (request.POST if request.method == "POST" else request.GET).get(
        "from"
    ) == "ticket"
    context = _report_context(request, ticket_id, kind, now)
    if context is None:
        return _not_found(request, now)
    sheet = _record_sheet(context, ticket_id, kind, from_ticket, now)
    status = 200
    if request.method == "POST":
        values = {
            "submitted_at": request.POST.get("submitted_at", "").strip(),
            "reference": request.POST.get("reference", "").strip(),
        }
        body = {}
        if values["submitted_at"]:
            body["submitted_at"] = rp.api_time(values["submitted_at"])
        if values["reference"]:
            body["reference"] = values["reference"]
        result = call_api(
            request, "POST", f"/tickets/{ticket_id}/reports/{kind}/submission", body=body
        )
        if result.ok:
            late = result.data.get("status") == "submitted_late"
            flash(
                request,
                f"{rp.LABEL[kind]} recorded",
                ("Submitted late." if late else "Submitted on time.")
                + " The report is locked as it read now.",
            )
            return redirect("console:ticket", ticket_id)
        if result.status == 404:
            return _not_found(request, now)
        errors, missing, problem = rp.record_errors(result.data, sheet["aware"])
        sheet.update(values=values, errors=errors, problem=problem)
        if missing:
            sheet["missing"] = [rp.field_label(f) for f in missing]
            sheet["missing_first"] = missing[0]
        status = result.status
    if from_ticket:
        page, found = ticket_context(request, ticket_id, now)
        if not found:
            return _not_found(request, now)
        page["sheet"] = "record"
        return render(request, "console/ticket_record.html", {**page, "rs": sheet}, status=status)
    context["sheet"] = "record"
    return render(request, "console/report.html", {**context, "rs": sheet}, status=status)


@never_cache
@signed_in_required
@require_http_methods(["GET", "HEAD", "POST"])
def close(request, ticket_id: str):
    now = clock.now()
    problem, status = "", 200
    if request.method == "POST":
        result = call_api(request, "POST", f"/tickets/{ticket_id}/close")
        if result.ok:
            flash(
                request,
                "Ticket closed",
                f"{result.data['title']} is resolved. The audit trail records it.",
            )
            return redirect("console:ticket", ticket_id)
        if result.status != 404:
            problem = (result.data or {}).get("detail") or "The ticket couldn't be closed."
            status = result.status
    page, found = ticket_context(request, ticket_id, now)
    if not found:
        return render(request, "console/not_found.html", page, status=404)
    page.update(sheet="close", close_problem=problem)
    return render(request, "console/ticket.html", page, status=status)
