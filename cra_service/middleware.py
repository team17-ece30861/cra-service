import hmac

from django.conf import settings
from django.db import transaction
from django.http import HttpRequest, HttpResponse

from cra_service.errors import PROBLEM_CONTENT_TYPE, problem_response

MAX_BODY_BYTES = 65_536

# Every other request needs a client's bearer token (openapi.yaml `security`).
PUBLIC_ROUTES = {("GET", "/health")}

# WSGI environ key holding the matched client's name. gunicorn's access log reads
# it as %({cra_service.client}e)s (gunicorn.conf.py).
CLIENT_ENVIRON_KEY = "cra_service.client"

# Reads never change data, so they skip the transaction (and GET /health never
# opens a database connection, which would wake Neon).
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

# Headers worth keeping when an error response is rewritten as a problem.
_KEPT_HEADERS = ("Allow", "WWW-Authenticate", "Retry-After")


class PlatformMiddleware:
    """Runs before URL routing so that 401, then 413, win over 404 and 405, as
    openapi.yaml's precedence requires.

    Requests that may write run in one transaction that is rolled back if the
    response is an error, so a failed request changes nothing. Ninja turns
    exceptions into responses inside the view, so a rollback keyed on the
    exception (ATOMIC_REQUESTS) would miss them.

    Finally, any error response that is not already problem+json (Django's 404
    and 500 pages, ninja's 405) is rewritten so every error has the same shape
    and none leaks details."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.client_name = _client_name(request)
        if request.client_name:
            # request.META is the WSGI environ that gunicorn logs from.
            request.META[CLIENT_ENVIRON_KEY] = request.client_name
        elif (request.method, request.path_info) not in PUBLIC_ROUTES:
            return problem_response(401, headers={"WWW-Authenticate": "Bearer"})
        if _content_length(request) > MAX_BODY_BYTES:
            return problem_response(413)
        if request.method in SAFE_METHODS:
            return _as_problem(self.get_response(request))
        with transaction.atomic():
            response = self.get_response(request)
            if response.status_code >= 400:
                transaction.set_rollback(True)
        return _as_problem(response)


def _client_name(request: HttpRequest) -> str | None:
    """The name of the client whose token the request carries, or None. With no
    tokens configured nothing matches, so the service fails closed."""
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer":
        return None
    presented = token.strip().encode("utf-8", "surrogatepass")
    matched = None
    # Compare against every token, so the time taken doesn't depend on which matched.
    for name, expected in settings.API_TOKENS.items():
        if expected and hmac.compare_digest(presented, expected.encode("utf-8", "surrogatepass")):
            matched = matched or name
    return matched


def _content_length(request: HttpRequest) -> int:
    # Checked before anything reads the body. Without a valid Content-Length,
    # Django reads no body at all, so there is nothing to limit.
    try:
        return int(request.META.get("CONTENT_LENGTH") or 0)
    except ValueError:
        return 0


def _as_problem(response: HttpResponse) -> HttpResponse:
    if response.status_code < 400 or response.get("Content-Type", "").startswith(
        PROBLEM_CONTENT_TYPE
    ):
        return response
    headers = {h: response[h] for h in _KEPT_HEADERS if response.has_header(h)}
    return problem_response(response.status_code, headers=headers)
