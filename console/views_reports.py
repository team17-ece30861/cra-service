"""Report pages (4.U3): the Report Draft page, the Record Submission sheet and the Close
Ticket dialog. Each sheet has its own address, so it can be bookmarked or reloaded: the GET
renders the page it belongs to with the sheet open, and ledger's reports.js opens and closes
it in place when it's clicked from that page. A POST makes exactly one change through the
API, as the signed-in person; a failure re-renders the sheet with the API's errors."""

from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from console import present
from console import present_reports as rp
from console.api_calls import call_api
from console.flash import flash
from console.views import (
    _everything,
    _failed_status,
    _shell,
    signed_in_required,
    ticket_context,
)
from core import clock

# reports.js sends SHEET_HEADER with a sheet's POST; success answers with DONE_HEADER.
SHEET_HEADER = "X-Ledger-Sheet"
DONE_HEADER = "X-Ledger-Done"


def _instead(request, now, *, failed=None):
    """The page to send instead of a report page: not found, or a read that failed (as the
    ticket page does)."""
    _, rows, groups, upcoming = _everything(request, now)
    context = _shell(request, "ticket", rows, groups, upcoming, now)
    if failed is None:
        return render(request, "console/not_found.html", context, status=404)
    context["message"] = "This report couldn't be loaded. Reload the page to try again."
    return render(request, "console/error.html", context, status=_failed_status(failed))


def _read_draft(request, ticket_id: str, kind: str, now):
    """The draft as the page shows it, why there's none (the API's 409 for a ticket that
    never became reportable), and the response to send instead when the read failed."""
    draft = call_api(request, "GET", f"/tickets/{ticket_id}/reports/{kind}")
    if draft.status == 404:
        return None, "", _instead(request, now)
    if not draft.ok and draft.status != 409:
        return None, "", _instead(request, now, failed=draft)
    if not draft.ok:
        return None, (draft.data or {}).get("detail") or "", None
    return rp.draft_view(draft.data, now), "", None


def _report_context(request, ticket_id: str, kind: str, now):
    """The Report Draft page for one report type, and None; or None and the response to
    send instead (no such ticket or type, or a read that failed)."""
    if kind not in rp.REPORT_TYPES:
        return None, _instead(request, now)
    found = call_api(request, "GET", f"/tickets/{ticket_id}")
    if found.status == 404:
        return None, _instead(request, now)
    if not found.ok:
        return None, _instead(request, now, failed=found)
    d, no_draft, instead = _read_draft(request, ticket_id, kind, now)
    if instead is not None:
        return None, instead
    t = found.data
    _, rows, groups, upcoming = _everything(request, now)
    # Only what the report pages show: the reporter stays on the ticket page.
    ticket = {"id": t["id"], "title": t["title"], "state": t["state"]}
    return {
        **_shell(request, "report", rows, groups, upcoming, now),
        "ticket": ticket,
        "ticket_title": ticket["title"],
        "kind": kind,
        "tabs": rp.tabs(ticket_id, kind),
        "d": d,
        "no_draft": no_draft,
        "kind_label": rp.LABEL[kind],
        "kind_title": rp.TITLE[kind],
    }, None


@never_cache
@signed_in_required
@require_http_methods(["GET", "HEAD"])
def report(request, ticket_id: str, kind: str):
    now = clock.now()
    context, instead = _report_context(request, ticket_id, kind, now)
    if instead is not None:
        return instead
    if context["d"] and context["d"]["recordable"]:
        # Ready to open in place from Record Submission.
        context["rs"] = _record_sheet(context, ticket_id, kind, False, now)
    return render(request, "console/report.html", context)


def _record_sheet(context: dict, ticket_id: str, kind: str, from_ticket: bool, now) -> dict:
    """The Record Submission sheet over the page it was opened from. `context` has the
    draft (`d`, `no_draft`) and the ticket's title."""
    d = context.get("d") or {}
    if from_ticket:
        base = reverse("console:ticket", args=[ticket_id])
    else:
        base = reverse("console:report", args=[ticket_id, kind])
    return {
        "type": kind,
        "label": rp.LABEL[kind],
        "title": rp.TITLE[kind],
        "ticket_title": context["ticket_title"],
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
        "values": {"submitted_at": rp.ui_time(present.iso(now)), "reference": ""},
        "errors": {},
        "problem": "",
    }


def _done(request, ticket_id: str):
    """After a change: the ticket page, where the toast waits. The page's own script asks
    with X-Ledger-Sheet and gets the address in a header instead of a redirect it can't
    read, so it can tell success from a redirect to sign-in (reports.js)."""
    url = reverse("console:ticket", args=[ticket_id])
    if request.headers.get(SHEET_HEADER):
        response = HttpResponse(status=204)
        response[DONE_HEADER] = url
        return response
    return redirect(url)


@never_cache
@signed_in_required
@require_http_methods(["GET", "HEAD", "POST"])
def record(request, ticket_id: str, kind: str):
    now = clock.now()
    if kind not in rp.REPORT_TYPES or kind == "user_advisory":
        return _instead(request, now)  # nothing to record: the API's 404 too
    asked = request.POST if request.method == "POST" else request.GET
    from_ticket = asked.get("from") == "ticket"
    status, values, errors, problem, missing = 200, None, {}, "", []
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
            return _done(request, ticket_id)
        if result.status == 404:
            return _instead(request, now)
        status, failed = result.status, result.data
    # The page under the sheet, read once (a failed change changed nothing).
    if from_ticket:
        page, instead = ticket_context(request, ticket_id, now)
        if instead is not None:
            return instead
        d, no_draft, instead = _read_draft(request, ticket_id, kind, now)
        if instead is not None:
            return instead
        page.update(d=d, no_draft=no_draft, ticket_title=page["t"]["title"])
        template = "console/ticket_record.html"
    else:
        page, instead = _report_context(request, ticket_id, kind, now)
        if instead is not None:
            return instead
        template = "console/report.html"
    sheet = _record_sheet(page, ticket_id, kind, from_ticket, now)
    if values is not None:
        errors, missing, problem = rp.record_errors(failed, sheet["aware"])
        sheet.update(values=values, errors=errors, problem=problem)
        if missing:
            sheet["missing"] = [rp.field_label(f) for f in missing]
            sheet["missing_first"] = missing[0]
    page["sheet"] = "record"
    return render(request, template, {**page, "rs": sheet}, status=status)


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
            return _done(request, ticket_id)
        if result.status != 404:
            problem = (result.data or {}).get("detail") or "The ticket couldn't be closed."
            status = result.status
    page, instead = ticket_context(request, ticket_id, now)
    if instead is not None:
        return instead
    page.update(sheet="close", close_problem=problem)
    return render(request, "console/ticket.html", page, status=status)
