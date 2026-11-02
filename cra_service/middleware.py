import hmac
import json
from http import HTTPStatus

from django.conf import settings
from django.db import transaction
from django.http import HttpRequest, HttpResponse

from cra_service.errors import PROBLEM_CONTENT_TYPE, problem_response

MAX_BODY_BYTES = 65_536

# Every other request needs a client's bearer token (openapi.yaml `security`).
PUBLIC_ROUTES = {("GET", "/health")}

# The console's pages and its static files sign people in with a session instead of a
# token (docs/plan.md, 4.U1). Only these exact prefixes: a session never unlocks the API.
CONSOLE_PATHS = ("/console/", "/static/")
CONSOLE_CLIENT = "console"

# WSGI environ key holding the matched client's name. gunicorn's access log reads
# it as %({cra_service.client}e)s (gunicorn.conf.py).
CLIENT_ENVIRON_KEY = "cra_service.client"

# Reads never change data, so they skip the transaction (and GET /health never
# opens a database connection, which would wake Neon).
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

# The tester's routes manage their own writes: a run lasts minutes, and its session
# state must be visible to other requests (409 while running) before it ends.
NO_TRANSACTION_PREFIX = "/tester/"

# The course's cross-team testing interface: its system endpoints and our tester. The
# course spec requires a non-empty `message` and a `source` on every error from these,
# including 401s, unknown routes, and server errors that never reach their own handlers.
# Other paths (the pod's /test/reset and /test/clock included) keep the pod contract's
# plain problem body.
INTERFACE_SYSTEM_PATHS = {"/test/setup", "/test/report"}
INTERFACE_TESTER_PREFIX = "/tester/"

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
        if _is_console(request.path_info):
            return self._console(request)
        return _with_interface_fields(request.path_info, self._api(request))

    def _api(self, request: HttpRequest) -> HttpResponse:
        request.client_name = _client_name(request)
        if request.client_name:
            # request.META is the WSGI environ that gunicorn logs from.
            request.META[CLIENT_ENVIRON_KEY] = request.client_name
        elif (request.method, request.path_info) not in PUBLIC_ROUTES:
            return problem_response(401, headers={"WWW-Authenticate": "Bearer"})
        if _content_length(request) > MAX_BODY_BYTES:
            return problem_response(413)
        if request.method in SAFE_METHODS or request.path_info.startswith(NO_TRANSACTION_PREFIX):
            return _as_problem(self.get_response(request))
        with transaction.atomic():
            response = self.get_response(request)
            if response.status_code >= 400:
                transaction.set_rollback(True)
        return _as_problem(response)

    def _console(self, request: HttpRequest) -> HttpResponse:
        """Console pages: no token (the pages check the session), the same body limit, and
        the same rule that a failed request changes nothing. Their errors are pages, not
        problem+json."""
        request.client_name = CONSOLE_CLIENT
        request.META[CLIENT_ENVIRON_KEY] = CONSOLE_CLIENT
        if _content_length(request) > MAX_BODY_BYTES:
            return problem_response(413)
        if request.method in SAFE_METHODS:
            return self.get_response(request)
        with transaction.atomic():
            response = self.get_response(request)
            if response.status_code >= 400:
                transaction.set_rollback(True)
        return response


def _is_console(path: str) -> bool:
    return path == "/console" or path.startswith(CONSOLE_PATHS)


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


def _interface_source(path: str) -> str | None:
    if path in INTERFACE_SYSTEM_PATHS:
        return "system"
    if path.startswith(INTERFACE_TESTER_PREFIX):
        return "tester"
    return None


def _with_interface_fields(path: str, response: HttpResponse) -> HttpResponse:
    """Adds `message` and `source` to an error from the testing interface that doesn't
    already have them. Bodies that already carry them (a forwarded system error, say),
    and anything that isn't a JSON problem object, are left as they are."""
    source = _interface_source(path)
    if (
        source is None
        or response.status_code < 400
        or response.streaming
        or not response.get("Content-Type", "").startswith(PROBLEM_CONTENT_TYPE)
    ):
        return response
    try:
        body = json.loads(response.content)
    except ValueError:
        return response
    if not isinstance(body, dict) or (body.get("message") and body.get("source")):
        return response
    body["message"] = (
        body.get("message")
        or body.get("detail")
        or body.get("title")
        or HTTPStatus(response.status_code).phrase
    )
    body["source"] = body.get("source") or source
    response.content = json.dumps(body)
    # CommonMiddleware (inside this one) already set Content-Length for the old body, and
    # gunicorn sends no more bytes than it says.
    if response.has_header("Content-Length"):
        response["Content-Length"] = str(len(response.content))
    return response
