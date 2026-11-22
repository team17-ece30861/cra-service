"""Toasts after a change (docs/design.md, "Toasts"). The one mechanism for every sheet:

- Saved from the page's own script (it sends SHEET_HEADER): the answer is JSON with the
  toast, and the script closes the sheet, shows the toast and refreshes the page in place
  (ledger.js, "Sheets"). Nothing waits in the session, so no stale toast shows up later.
- Saved without JavaScript (a plain form POST): the toast waits in the session and the
  browser is redirected; the page it lands on shows it once (POST/redirect/GET)."""

from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse

KEY = "ledger_toast"
SHEET_HEADER = "X-Ledger-Sheet"


def flash(request, title: str, body: str = "") -> None:
    request.session[KEY] = {"title": title, "body": body}


def take(request) -> dict | None:
    """The waiting toast, if any; it's gone once taken."""
    return request.session.pop(KEY, None) if hasattr(request, "session") else None


def saved(request, ticket_id: str, title: str, body: str = ""):
    """The answer to a change that went through: JSON for the page's script (which stays on
    the page under the sheet), or the toast in the session and a redirect to the ticket for
    a plain form POST."""
    if request.headers.get(SHEET_HEADER):
        return JsonResponse({"saved": True, "toast": {"title": title, "body": body}})
    flash(request, title, body)
    return redirect(reverse("console:ticket", args=[ticket_id]))
