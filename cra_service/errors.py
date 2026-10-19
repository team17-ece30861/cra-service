"""Problem details (RFC 9457) for every error the service returns.

Views raise one of the ApiError subclasses; the handlers installed on the API turn
them into application/problem+json responses. 400 and 422 always carry a non-empty
`errors` list of {field, message}. Don't return a 4xx body directly:
cra_service.middleware replaces any error response that isn't problem+json with a
generic one, dropping its detail and errors.

When several errors apply, openapi.yaml requires the first of 401, 413, 404, 400,
409, 422. 401 and 413 are enforced by cra_service.middleware before routing. Views
get the rest by checking in that order: look the resource up (404), then validate
the X-Actor header and body (400, see cra_service.validation), then state (409),
then rules (422). Any error response rolls back the request's writes
(cra_service.middleware).
"""

import json
import logging
import traceback
from http import HTTPStatus

from django.http import Http404, HttpRequest, HttpResponse
from ninja.errors import HttpError, ValidationError

logger = logging.getLogger(__name__)

PROBLEM_CONTENT_TYPE = "application/problem+json"

TITLES = {
    400: "Invalid request",
    401: "Unauthorized",
    404: "Not found",
    405: "Method not allowed",
    409: "Conflict",
    413: "Payload too large",
    422: "Rule violation",
    500: "Internal server error",
}

FieldError = dict[str, str]


def field_error(field: str, message: str) -> FieldError:
    return {"field": field, "message": message}


class ApiError(Exception):
    status = 500

    def __init__(self, detail: str | None = None, errors: list[FieldError] | None = None):
        super().__init__(detail or TITLES.get(self.status, ""))
        self.detail = detail
        self.errors = errors


class _ErrorsRequired(ApiError):
    def __init__(self, errors: list[FieldError], detail: str | None = None):
        if not errors:
            raise ValueError(f"{type(self).__name__} needs at least one field error")
        unique = list({(e["field"], e["message"]): e for e in errors}.values())
        super().__init__(detail, unique)


class BadRequest(_ErrorsRequired):
    """The request does not match the schema."""

    status = 400


class NotFound(ApiError):
    status = 404


class Conflict(ApiError):
    """Not allowed in the resource's current state."""

    status = 409


class RuleViolation(_ErrorsRequired):
    """A valid request that breaks a business rule."""

    status = 422


def problem_response(
    status: int,
    *,
    detail: str | None = None,
    errors: list[FieldError] | None = None,
    headers: dict[str, str] | None = None,
    extra: dict | None = None,
) -> HttpResponse:
    body: dict = {"title": TITLES.get(status) or HTTPStatus(status).phrase, "status": status}
    if detail:
        body["detail"] = detail
    if status in (400, 422):
        body["errors"] = errors or [field_error("request", "is invalid")]
    elif errors:
        body["errors"] = errors
    if extra:
        body.update(extra)
    return HttpResponse(
        json.dumps(body), status=status, content_type=PROBLEM_CONTENT_TYPE, headers=headers
    )


def interface_problem(
    status: int, message: str, source: str, errors: list[FieldError] | None = None
) -> HttpResponse:
    """An error from the course's cross-team testing interface (/test/setup,
    /test/report, and the tester under /tester). That interface requires a non-empty
    `message` and a `source` (tester, system, communication, or unknown), which are
    added to the usual problem fields."""
    return problem_response(
        status, detail=message, errors=errors, extra={"message": message, "source": source}
    )


def server_error(request: HttpRequest) -> HttpResponse:
    """Django's handler500, for exceptions raised outside the API's own handlers."""
    return problem_response(500)


def _respond(exc: ApiError) -> HttpResponse:
    return problem_response(exc.status, detail=exc.detail, errors=exc.errors)


def _on_api_error(request: HttpRequest, exc: ApiError) -> HttpResponse:
    return _respond(exc)


def _on_validation_error(request: HttpRequest, exc: ValidationError) -> HttpResponse:
    # Ninja's 422. Entries come from ServiceAPI.validation_error_from_error_contexts.
    # A path parameter that fails validation (e.g. an unknown report type) is a 404.
    if any(e["source"] == "path" for e in exc.errors):
        return _respond(NotFound())
    return _respond(BadRequest([field_error(e["field"], e["message"]) for e in exc.errors]))


def _on_http_error(request: HttpRequest, exc: HttpError) -> HttpResponse:
    # Ninja wraps body-parser failures in HttpError(400) and, under DEBUG, appends
    # the parser's message, so never echo exc.message.
    if isinstance(exc.__cause__, ApiError):
        return _respond(exc.__cause__)
    if exc.status_code == 400:
        return _respond(BadRequest([field_error("body", "must be valid JSON")]))
    return problem_response(exc.status_code)


def _on_not_found(request: HttpRequest, exc: Http404) -> HttpResponse:
    return _respond(NotFound())


def _on_unhandled(request: HttpRequest, exc: Exception) -> HttpResponse:
    # Log the type and stack only. Exception messages can quote request data
    # (pydantic and database errors do), and request bodies must never be logged.
    logger.error(
        "Unhandled %s on %s %s\n%s",
        type(exc).__qualname__,
        request.method,
        request.path,
        "".join(traceback.format_tb(exc.__traceback__)),
    )
    return problem_response(500)


def install_exception_handlers(api) -> None:
    api.add_exception_handler(Exception, _on_unhandled)
    api.add_exception_handler(ApiError, _on_api_error)
    api.add_exception_handler(ValidationError, _on_validation_error)
    api.add_exception_handler(HttpError, _on_http_error)
    api.add_exception_handler(Http404, _on_not_found)
