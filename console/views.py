from functools import wraps
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods, require_POST

from console.mark import MARK_PATH, MARK_VIEWBOX

# Remembers that this browser was signed in, so a person whose session ended sees
# "Signed out" instead of a bare sign-in page. It holds no identity.
WAS_SIGNED_IN_COOKIE = "ledger_was_signed_in"
WAS_SIGNED_IN_MAX_AGE = 30 * 24 * 3600
BAD_SIGN_IN = "That username and password don't match."


def _home() -> str:
    return reverse("console:tickets")


def _safe_next(request, value: str) -> str:
    """Only console pages on this host; anything else goes to Tickets."""
    allowed = url_has_allowed_host_and_scheme(
        value, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    )
    return value if value and allowed and value.startswith("/console/") else _home()


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


@never_cache
@signed_in_required
def tickets(request):
    return render(request, "console/tickets.html")
