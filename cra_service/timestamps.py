"""Timestamps as openapi.yaml defines them.

Input: RFC 3339 with seconds and any UTC offset. Fractional seconds are accepted
and truncated (AC-14). Values without seconds or without an offset are rejected.
Output: always UTC to the second, e.g. 2026-10-05T09:00:00Z.

Use `Timestamp` as the field type in schemas. It parses on input and formats on
output, so views and models only ever see aware UTC datetimes with microsecond=0.
"""

import re
from datetime import UTC, datetime, timedelta, timezone
from typing import Annotated, Any

from pydantic import PlainSerializer, PlainValidator, WithJsonSchema
from pydantic_core import PydanticCustomError

# [0-9] rather than \d, which also matches non-ASCII digits.
_DATE_TIME = r"[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt][0-9]{2}:[0-9]{2}"
_OFFSET = r"(?:[Zz]|[+-][0-9]{2}:[0-9]{2})"
_RFC3339 = re.compile(
    r"(?P<year>[0-9]{4})-(?P<month>[0-9]{2})-(?P<day>[0-9]{2})[Tt]"
    r"(?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):(?P<second>[0-9]{2})(?:\.[0-9]+)?"
    r"(?P<offset>[Zz]|(?P<sign>[+-])(?P<off_hour>[0-9]{2}):(?P<off_minute>[0-9]{2}))"
)
_MISSING_SECONDS = re.compile(_DATE_TIME + _OFFSET + "?")
_MISSING_OFFSET = re.compile(_DATE_TIME + r":[0-9]{2}(?:\.[0-9]+)?")

EXAMPLE = "2026-10-05T09:00:00Z"


def parse_timestamp(value: str) -> datetime:
    """Parse an RFC 3339 timestamp into an aware UTC datetime truncated to the second.

    Raises ValueError with a message suitable for an API error.
    """
    match = _RFC3339.fullmatch(value)
    if match is None:
        if _MISSING_SECONDS.fullmatch(value):
            raise ValueError("must include seconds")
        if _MISSING_OFFSET.fullmatch(value):
            raise ValueError("must include a UTC offset (Z or +hh:mm)")
        raise ValueError(f"must be an RFC 3339 timestamp such as {EXAMPLE}")

    if match["sign"] is None:
        tz = UTC
    else:
        off_hour, off_minute = int(match["off_hour"]), int(match["off_minute"])
        if off_hour > 23 or off_minute > 59:
            raise ValueError("has an invalid UTC offset")
        offset = timedelta(hours=off_hour, minutes=off_minute)
        tz = timezone(-offset if match["sign"] == "-" else offset)

    fields = ("year", "month", "day", "hour", "minute", "second")
    try:
        local = datetime(*(int(match[f]) for f in fields), tzinfo=tz)
    except ValueError:
        raise ValueError("is not a valid date and time") from None
    try:
        return local.astimezone(UTC)
    except (OverflowError, ValueError):
        raise ValueError("is out of range") from None


def to_utc_second(value: datetime) -> datetime:
    """Convert an aware datetime to UTC and drop fractional seconds."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("naive datetime; all times must be timezone-aware")
    return value.astimezone(UTC).replace(microsecond=0)


def format_timestamp(value: datetime) -> str:
    """Format as UTC to the second: 2026-10-05T09:00:00Z."""
    v = to_utc_second(value)
    return f"{v.year:04d}-{v.month:02d}-{v.day:02d}T{v.hour:02d}:{v.minute:02d}:{v.second:02d}Z"


def _validate(value: Any) -> datetime:
    if isinstance(value, datetime):
        try:
            return to_utc_second(value)
        except ValueError as exc:
            raise PydanticCustomError("timestamp", str(exc)) from None
    if not isinstance(value, str):
        raise PydanticCustomError("timestamp", f"must be an RFC 3339 timestamp such as {EXAMPLE}")
    try:
        return parse_timestamp(value)
    except ValueError as exc:
        raise PydanticCustomError("timestamp", str(exc)) from None


Timestamp = Annotated[
    datetime,
    PlainValidator(_validate),
    PlainSerializer(format_timestamp, return_type=str),
    WithJsonSchema({"type": "string", "format": "date-time", "examples": [EXAMPLE]}),
]
