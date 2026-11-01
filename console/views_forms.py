"""New Ticket, Edit Ticket and Triage (4.U2 part 2). Each is a sheet over the page it
belongs to: GET renders that page with the sheet open (so the URL can be bookmarked or
linked, e.g. /console/tickets/<id>/edit?focus=member_states), and the page's own JS opens
the same sheet in place. A POST makes exactly one change through the API. If the API says
no, the sheet comes back with the person's input and the API's errors under the fields; if
it says yes, the browser is redirected to the ticket with a toast (POST/redirect/GET)."""

import json

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from console import forms, present, views
from console.api_calls import call_api
from core import clock

TOAST_TAG = "ledger-toast"
OUT_OF_DATE = "This form is out of date. Your changes weren't saved; make them again here."
CHANGED_MEANWHILE = (
    "Someone else changed this since you opened the sheet. Save again to replace it."
)
READ_FAILED = (
    "This ticket couldn't be loaded, so nothing was changed. Reload the page to try again."
)


def _toast(request, title: str, body: str) -> None:
    """Shown once, on the next page (console/templates/console/shell.html)."""
    messages.success(request, json.dumps({"title": title, "body": body}), extra_tags=TOAST_TAG)


def _ticket_page(request, ticket_id: str):
    """The Ticket page (views.ticket_context) as (template, context, status), or
    (None, response, status) when another page goes instead: not found, or a failed read."""
    context, instead = views.ticket_context(request, ticket_id, clock.now())
    if instead is not None:
        return None, instead, instead.status_code
    return "console/ticket.html", context, 200


def _read_failed(request, ticket_id: str, found):
    """The ticket read before a change failed: not found, or PR 1's error page."""
    if found.status == 404:
        return _over(request, _ticket_page(request, ticket_id), "", {})
    now = clock.now()
    _, rows, groups, upcoming = views._everything(request, now)
    context = {
        **views._shell(request, "ticket", rows, groups, upcoming, now),
        "message": READ_FAILED,
    }
    return render(request, "console/error.html", context, status=views._failed_status(found))


def _over(request, page, sheet: str, extra: dict, *, status=None, enter=False):
    """The page with one of its sheets open. ``enter``: the sheet rises in (a fresh GET);
    otherwise it's simply there (the answer to a POST)."""
    template, context, page_status = page
    if template is None:  # the ticket wasn't found or couldn't be read: that page instead
        return context
    context.update(extra)
    context["open_sheet"] = sheet
    context["sheet_enter"] = enter
    return render(request, template, context, status=status or page_status)


@never_cache
@views.signed_in_required
@require_http_methods(["GET", "HEAD", "POST"])
def new_ticket(request):
    if request.method != "POST":
        page = views.tickets_page(request)
        return _over(request, page, "new", {}, enter=True)
    values = forms.values_from_post(request.POST)
    result = call_api(request, "POST", "/tickets", body=forms.create_body(values))
    if result.ok:
        _toast(
            request,
            "Ticket created",
            f"\N{LEFT DOUBLE QUOTATION MARK}{result.data['title']}\N{RIGHT DOUBLE QUOTATION MARK}"
            " is in To Triage. Its received time is now.",
        )
        return redirect("console:ticket", result.data["id"])
    problems = forms.problems(result, forms.NEW_KNOWN, clock.now())
    page = views.tickets_page(request)
    return _over(request, page, "new", forms.new_sheet(values, problems), status=result.status)


@never_cache
@views.signed_in_required
@require_http_methods(["GET", "HEAD", "POST"])
def edit_ticket(request, ticket_id: str):
    if request.method != "POST":
        page = _ticket_page(request, ticket_id)
        extra = {}
        if page[0] is not None:
            ticket = page[1]["t"]
            current = forms.values_from_ticket(ticket)
            extra["tf_edit"] = forms.ticket_form(
                "edit",
                values=current,
                initial=current,
                ticket=ticket,
                focus=request.GET.get("focus", ""),
            )
        return _over(request, page, "edit", extra, enter=True)
    found = call_api(request, "GET", f"/tickets/{ticket_id}")
    if not found.ok:
        return _read_failed(request, ticket_id, found)
    ticket = found.data
    current = forms.values_from_ticket(ticket)
    original = forms.read_original(request.POST.get("original", ""))
    if original is None:  # not a form this console rendered: start again from the ticket
        problems = forms.Problems(general=OUT_OF_DATE)
        sheet = forms.ticket_form(
            "edit", values=current, initial=current, problems=problems, ticket=ticket
        )
        return _over(
            request, _ticket_page(request, ticket_id), "edit", {"tf_edit": sheet}, status=400
        )
    values = forms.values_from_post(request.POST)
    values["change_reason"] = forms.clean(request.POST.get("change_reason", ""))
    # Only what this person changed, against what they saw; never a field someone else
    # changed meanwhile.
    changed = forms.changed_keys(original, values)
    clashes = forms.conflicts(changed, original, current, values)
    values = forms.merged(changed, values, current)
    body = forms.update_body(changed, values) if changed and not clashes else {}
    if clashes:
        problems = forms.Problems(
            fields={k: CHANGED_MEANWHILE for k in clashes if k in forms.edit_known(ticket)},
            general="Someone else changed this ticket while you were editing. Nothing was saved.",
        )
        status = 409
    elif not body:
        problems, status = forms.Problems(general="Change a field to save."), 200
    else:
        result = call_api(request, "PATCH", f"/tickets/{ticket_id}", body=body)
        if result.ok:
            n = len(changed)
            _toast(
                request,
                "Ticket updated",
                f"{n} field{'' if n == 1 else 's'} changed. "
                "The audit trail records it with your username.",
            )
            return redirect("console:ticket", ticket_id)
        problems = forms.problems(result, forms.edit_known(ticket), clock.now())
        forms.explain_partial_clears(problems, current, values)
        status = result.status
    sheet = forms.ticket_form(
        "edit", values=values, initial=current, problems=problems, ticket=ticket
    )
    page = _ticket_page(request, ticket_id)
    return _over(request, page, "edit", {"tf_edit": sheet}, status=status)


@never_cache
@views.signed_in_required
@require_http_methods(["GET", "HEAD", "POST"])
def triage(request, ticket_id: str):
    if request.method != "POST":
        return _over(request, _ticket_page(request, ticket_id), "triage", {}, enter=True)
    found = call_api(request, "GET", f"/tickets/{ticket_id}")
    if not found.ok:
        return _read_failed(request, ticket_id, found)
    title = found.data["title"]
    result = call_api(
        request, "POST", f"/tickets/{ticket_id}/triage", body=forms.triage_body(request.POST)
    )
    if result.ok:
        if result.data["state"] == "reportable":
            due = present.utc(result.data["obligations"]["early_warning"]["due_at"])
            _toast(
                request,
                "Triaged as actively exploited",
                f"{title} is reportable. Early warning due {due}.",
            )
        else:
            what = present.RESOLUTION_LABEL.get(result.data.get("resolution"), "").lower()
            _toast(request, f"Closed as {what}", f"{title} is closed. No reports are needed.")
        return redirect("console:ticket", ticket_id)
    problems = forms.problems(result, forms.TRIAGE_FIELDS, clock.now())
    sheet = forms.triage_form(found.data, post=request.POST, problems=problems)
    page = _ticket_page(request, ticket_id)
    return _over(request, page, "triage", {"tr": sheet}, status=result.status)
