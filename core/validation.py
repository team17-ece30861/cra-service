"""Request validation shared by every route.

Routes that change ticket data must return 404 for an unknown ticket before any
400 (openapi.yaml precedence). Ninja validates typed header and body parameters
before the view runs, so those routes take the raw request and validate in order:

    ticket = get_ticket_or_404(id)                  # 404
    actor = require_actor(request)                  # 400
    payload = parse_body(request, TicketUpdate)     # 400
    ...state checks (409), then rule checks (422)

Routes with no resource to look up (e.g. PUT /test/clock) can use typed ninja
parameters; ServiceAPI formats those errors the same way.
"""

import json
import re
from typing import Any

import pydantic
from django.http import HttpRequest
from ninja import Schema
from ninja.parser import Parser
from pydantic import ConfigDict

from core.errors import BadRequest, FieldError, field_error

ACTOR_HEADER = "X-Actor"
ACTOR_MAX_LENGTH = 200


class RequestSchema(Schema):
    """Base for request bodies and their nested objects. Unknown fields, including
    system-set ones such as `id` or `state`, are rejected with 400."""

    model_config = ConfigDict(extra="forbid")


def require_actor(request: HttpRequest) -> str:
    """The X-Actor header, required on every request that changes ticket data."""
    value = request.headers.get(ACTOR_HEADER)
    if value is None:
        message = "required"
    else:
        # HTTP strips surrounding whitespace from header values, so a blank
        # value is the same as an empty one.
        value = value.strip()
        if not value:
            message = "must not be empty"
        elif len(value) > ACTOR_MAX_LENGTH:
            message = f"must be at most {ACTOR_MAX_LENGTH} characters"
        else:
            return value
    raise BadRequest([field_error(ACTOR_HEADER, message)])


def parse_json(raw: bytes) -> Any:
    """Decode a UTF-8 JSON document, raising BadRequest if it is not valid JSON."""
    try:
        return json.loads(raw.decode("utf-8"), parse_constant=_reject_constant)
    except (ValueError, RecursionError):
        raise BadRequest([field_error("body", "must be valid JSON")]) from None


def _reject_constant(name: str) -> None:
    # Python's json accepts NaN and Infinity; JSON does not.
    raise ValueError(f"{name} is not valid JSON")


def parse_body[S: pydantic.BaseModel](
    request: HttpRequest, schema: type[S], *, required: bool = True
) -> S:
    """Parse and validate the JSON request body. An absent optional body is `{}`."""
    if request.body:
        data = parse_json(request.body)
    elif required:
        raise BadRequest([field_error("body", "required")])
    else:
        data = {}
    try:
        return schema.model_validate(data)
    except pydantic.ValidationError as exc:
        raise BadRequest(field_errors(exc.errors(include_url=False))) from None


class JSONParser(Parser):
    """Ninja body parser with the same strictness as parse_json."""

    def parse_body(self, request: HttpRequest) -> Any:
        return parse_json(request.body)


def field_errors(errors: list[dict], *, skip: int = 0, root: str = "body") -> list[FieldError]:
    """Convert pydantic error dicts to the API's [{field, message}] form.

    `skip` drops leading loc parts (ninja's parameter name); an error on the
    whole document is reported against `root`.
    """
    return [field_error(_field(e["loc"][skip:]) or root, _message(e)) for e in errors]


def _field(loc: tuple) -> str:
    # ("product", "affected_versions", 1) -> "product.affected_versions[1]"
    out = ""
    for part in loc:
        if isinstance(part, int):
            out += f"[{part}]"
        else:
            out += f".{part}" if out else str(part)
    return out


def _message(error: dict) -> str:
    kind = error["type"]
    ctx = error.get("ctx") or {}
    if kind == "missing":
        return "required"
    if kind == "extra_forbidden":
        return "not allowed"
    if kind in ("enum", "literal_error"):
        choices = re.findall(r"'([^']*)'", str(ctx.get("expected", "")))
        if choices:
            return "must be one of " + ", ".join(choices)
    if kind == "string_too_short":
        if ctx.get("min_length") == 1:
            return "must not be empty"
        return f"must be at least {ctx.get('min_length')} characters"
    if kind == "string_too_long":
        return f"must be at most {ctx.get('max_length')} characters"
    if kind == "too_short":
        return f"must have at least {ctx.get('min_length')} items"
    if kind == "too_long":
        return f"must have at most {ctx.get('max_length')} items"
    if kind == "string_type":
        return "must be a string"
    if kind == "list_type":
        return "must be an array"
    if kind in ("model_type", "model_attributes_type", "dict_type"):
        return "must be an object"
    if kind == "string_pattern_mismatch":
        return f"must match the pattern {ctx.get('pattern')}"
    message = error.get("msg", "is invalid")
    return message.removeprefix("Value error, ")
