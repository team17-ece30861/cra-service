import hmac

from django.conf import settings
from django.db import transaction
from django.http import HttpRequest, HttpResponse

from core.errors import PROBLEM_CONTENT_TYPE, problem_response

MAX_BODY_BYTES = 65_536

# Every other request needs the bearer token (openapi.yaml `security`).
PUBLIC_ROUTES = {("GET", "/health")}

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
        if (request.method, request.path_info) not in PUBLIC_ROUTES and not _has_valid_token(
            request
        ):
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


def _has_valid_token(request: HttpRequest) -> bool:
    expected = settings.API_TOKEN
    if not expected:
        return False  # fail closed if the deployment has no token configured
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer":
        return False
    return hmac.compare_digest(
        token.strip().encode("utf-8", "surrogatepass"),
        expected.encode("utf-8", "surrogatepass"),
    )


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
