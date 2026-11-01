import posixpath
from functools import wraps
from urllib.parse import unquote, urlencode, urlsplit

from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods, require_POST

from console import present
from console.api_calls import call_api
from console.mark import MARK_PATH, MARK_VIEWBOX
from core import clock
from core.models import FixedClock

# Remembers that this browser was signed in, so a person whose session ended sees
# "Signed out" instead of a bare sign-in page. It holds no identity.
WAS_SIGNED_IN_COOKIE = "ledger_was_signed_in"
WAS_SIGNED_IN_MAX_AGE = 30 * 24 * 3600
BAD_SIGN_IN = "That username and password don't match."


def _home() -> str:
    return reverse("console:tickets")


def _safe_next(request, value: str) -> str:
    """Only console pages on this host; anything else goes to Tickets. Dot segments
    are resolved first, so /console/../admin/ doesn't count as a console page."""
    allowed = url_has_allowed_host_and_scheme(
        value, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    )
    path = posixpath.normpath(unquote(urlsplit(value).path)) if value else ""
    in_console = value.startswith("/console/") and (path + "/").startswith("/console/")
    return value if allowed and in_console else _home()


def signed_in_required(view):
    """Console pages need a signed-in person; everyone else goes to sign-in and back."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view(request, *args, **kwargs)
        query = {"next": request.get_full_path()}
        if request.COOKIES.get(WAS_SIGNED_IN_COOKIE):
            query["signed-out"] = "1"
        return redirect(reverse("console:sign-in") + "?" + urlencode(query))

    return wrapper


@never_cache
@sensitive_post_parameters("password")
@require_http_methods(["GET", "POST"])
def sign_in(request):
    next_url = _safe_next(request, request.POST.get("next") or request.GET.get("next", ""))
    if request.method == "GET" and request.user.is_authenticated:
        return redirect(next_url)
    failed = False
    username = ""
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            response = redirect(next_url)
            response.set_cookie(
                WAS_SIGNED_IN_COOKIE,
                "1",
                max_age=WAS_SIGNED_IN_MAX_AGE,
                path=settings.SESSION_COOKIE_PATH,
                secure=settings.SESSION_COOKIE_SECURE,
                httponly=True,
                samesite="Lax",
            )
            return response
        failed = True
        username = request.POST.get("username", "")[:150]
    context = {
        "next": next_url,
        "username": username,
        "error": BAD_SIGN_IN if failed else "",
        "signed_out": request.GET.get("signed-out") == "1" and not failed,
        "mark_path": MARK_PATH,
        "mark_viewbox": MARK_VIEWBOX,
    }
    return render(request, "console/sign_in.html", context)


@require_POST
def sign_out(request):
    logout(request)
    response = redirect(reverse("console:sign-in") + "?signed-out=1")
    response.delete_cookie(WAS_SIGNED_IN_COOKIE, path=settings.SESSION_COOKIE_PATH)
    return response


# The dock's views of the list. Overdue and To Triage are the API's own filters; Due in 24 h
# and Closed are presentation (a due window, and the closed tickets the Home list leaves out).
VIEWS = {
    "overdue": ("Overdue", {"obligation_status": "overdue"}),
    "triage": ("To triage", {"state": "received"}),
    "due": ("Due in 24 h", {}),
    "closed": ("Closed", {"state": "closed"}),
}


def _shell(request, route: str, tickets: list[dict], now) -> dict:
    """What every signed-in page shows around its content (the island, dock and command
    field), from the unfiltered list. The page's "now" is the service clock's, never the
    browser's: the page ticks forward from it."""
    username = request.user.get_username()
    return {
        "route": route,
        "now_iso": present.iso(now),
        "now_utc": present.utc(present.iso(now)),
        "clock_fixed": FixedClock.objects.exists(),
        "username": username,
        "initials": present.initials(username),
        **present.shell(tickets, now),
    }


@never_cache
@signed_in_required
@require_http_methods(["GET", "HEAD"])
def tickets(request):
    now = clock.now()
    everything = call_api(request, "GET", "/tickets")
    all_tickets = everything.data if everything.ok else []
    view = request.GET.get("view", "")
    if view not in VIEWS:
        view = ""
    query = {k: request.GET[k] for k in ("state", "obligation_status") if request.GET.get(k)}
    title = ""
    if view:
        title, query = VIEWS[view][0], {**VIEWS[view][1], **query}
    elif query:
        labels = [present.STATE_LABEL.get(query.get("state", ""), "")]
        labels.append(present.STATUS.get(query.get("obligation_status", ""), ("", "", ""))[2])
        title = " · ".join(label for label in labels if label) or "Filtered"
    listed, problem = all_tickets, None
    if query:
        result = call_api(request, "GET", "/tickets", query=query)
        listed = result.data if result.ok else []
        problem = (
            None if result.ok else (result.data or {}).get("detail") or "That filter isn't valid."
        )
    groups = present.group_rows(listed, now)
    closed = next((g for g in groups if g["key"] == "closed"), None)
    if view == "due":
        groups = [g for g in groups if g["key"] == "today"]
    elif not query:
        groups = [g for g in groups if g["key"] != "closed"]
    upcoming = present.deadlines(all_tickets, now)
    context = {
        **_shell(request, "tickets", all_tickets, now),
        "view": view,
        "view_title": title,
        "filtered": bool(view or query),
        "problem": problem,
        "groups": groups,
        "listed_count": sum(len(g["rows"]) for g in groups),
        "closed_count": len(closed["rows"]) if closed and not query else 0,
        "hero": upcoming[0] if upcoming else None,
        "any_tickets": bool(all_tickets),
        "hero_on_page": bool(upcoming) and not (view or query),
        "dock_current": view or ("" if query else "all"),
    }
    return render(request, "console/tickets.html", context, status=400 if problem else 200)


@never_cache
@signed_in_required
@require_http_methods(["GET", "HEAD"])
def ticket(request, ticket_id: str):
    now = clock.now()
    everything = call_api(request, "GET", "/tickets")
    shell = _shell(request, "ticket", everything.data if everything.ok else [], now)
    found = call_api(request, "GET", f"/tickets/{ticket_id}")
    if found.status == 404:
        return render(request, "console/not_found.html", shell, status=404)
    data = found.data
    trail = call_api(request, "GET", f"/tickets/{ticket_id}/audit")
    cards = present.report_cards(data, now)
    report = present.next_report(data)
    context = {
        **shell,
        "t": data,
        "state_label": present.STATE_LABEL.get(data["state"], data["state"]),
        "resolution_label": present.RESOLUTION_LABEL.get(data.get("resolution") or ""),
        "source_label": present.SOURCE_LABEL.get(data.get("source"), data.get("source")),
        "tlp_class": present.TLP_CLASS.get(data.get("sensitivity") or "", ""),
        "received": present.utc(data.get("received_at")),
        "aware": present.utc(data.get("aware_at")),
        "fix_at": present.utc((data.get("fix") or {}).get("available_at")),
        "next": next((c for c in cards if c["type"] == report), None),
        "cards": cards,
        "audit": present.audit(trail.data if trail.ok else []),
    }
    return render(request, "console/ticket.html", context)
