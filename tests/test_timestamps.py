from datetime import UTC, datetime, timedelta, timezone

import pydantic
import pytest
from ninja import Schema

from core.timestamps import Timestamp, format_timestamp, parse_timestamp, to_utc_second


def utc(*args) -> datetime:
    return datetime(*args, tzinfo=UTC)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("2026-10-05T09:00:00Z", utc(2026, 10, 5, 9, 0, 0)),
        ("2026-10-05t09:00:00z", utc(2026, 10, 5, 9, 0, 0)),
        ("2026-10-05T11:00:00+02:00", utc(2026, 10, 5, 9, 0, 0)),
        ("2026-10-05T03:30:00-05:30", utc(2026, 10, 5, 9, 0, 0)),
        ("2026-10-05T09:00:00+00:00", utc(2026, 10, 5, 9, 0, 0)),
        ("2026-10-05T09:00:00-00:00", utc(2026, 10, 5, 9, 0, 0)),
        ("2026-10-05T00:30:00+01:00", utc(2026, 10, 4, 23, 30, 0)),  # crosses midnight
        ("2026-10-05T09:00:00.5Z", utc(2026, 10, 5, 9, 0, 0)),
        ("2026-10-05T09:00:00.999999999Z", utc(2026, 10, 5, 9, 0, 0)),  # truncated, not rounded
        ("2026-10-05T09:00:59.999+02:00", utc(2026, 10, 5, 7, 0, 59)),
        ("2028-02-29T12:00:00Z", utc(2028, 2, 29, 12, 0, 0)),
        ("2026-10-05T09:00:00+23:59", utc(2026, 10, 4, 9, 1, 0)),
    ],
)
def test_parses_rfc3339_with_any_offset(text, expected):
    parsed = parse_timestamp(text)
    assert parsed == expected
    assert parsed.tzinfo is UTC
    assert parsed.microsecond == 0


@pytest.mark.parametrize(
    "text,message",
    [
        ("2026-10-05T09:00Z", "must include seconds"),
        ("2026-10-05T09:00+02:00", "must include seconds"),
        ("2026-10-05T09:00", "must include seconds"),
        ("2026-10-05T09:00:00", "must include a UTC offset (Z or +hh:mm)"),
        ("2026-10-05T09:00:00.123", "must include a UTC offset (Z or +hh:mm)"),
        ("2026-10-05", "must be an RFC 3339 timestamp such as 2026-10-05T09:00:00Z"),
        ("2026-10-05 09:00:00Z", "must be an RFC 3339 timestamp such as 2026-10-05T09:00:00Z"),
        ("20261005T090000Z", "must be an RFC 3339 timestamp such as 2026-10-05T09:00:00Z"),
        ("2026-10-05T09:00:00+0200", "must be an RFC 3339 timestamp such as 2026-10-05T09:00:00Z"),
        ("2026-10-05T09:00:00+02", "must be an RFC 3339 timestamp such as 2026-10-05T09:00:00Z"),
        ("2026-10-05T09:00:00.Z", "must be an RFC 3339 timestamp such as 2026-10-05T09:00:00Z"),
        ("2026-10-05T09:00:00Z\n", "must be an RFC 3339 timestamp such as 2026-10-05T09:00:00Z"),
        (" 2026-10-05T09:00:00Z", "must be an RFC 3339 timestamp such as 2026-10-05T09:00:00Z"),
        ("२०२६-10-05T09:00:00Z", "must be an RFC 3339 timestamp such as 2026-10-05T09:00:00Z"),
        ("", "must be an RFC 3339 timestamp such as 2026-10-05T09:00:00Z"),
        ("2026-02-29T09:00:00Z", "is not a valid date and time"),
        ("2026-13-01T09:00:00Z", "is not a valid date and time"),
        ("2026-10-05T24:00:00Z", "is not a valid date and time"),
        ("2026-10-05T09:60:00Z", "is not a valid date and time"),
        ("2026-12-31T23:59:60Z", "is not a valid date and time"),  # leap second
        ("0000-01-01T00:00:00Z", "is not a valid date and time"),
        ("2026-10-05T09:00:00+24:00", "has an invalid UTC offset"),
        ("2026-10-05T09:00:00+02:60", "has an invalid UTC offset"),
        ("0001-01-01T00:00:00+01:00", "is out of range"),
        ("9999-12-31T23:59:59-01:00", "is out of range"),
    ],
)
def test_rejects_invalid_timestamps(text, message):
    with pytest.raises(ValueError) as excinfo:
        parse_timestamp(text)
    assert str(excinfo.value) == message


@pytest.mark.parametrize(
    "value,expected",
    [
        (utc(2026, 10, 5, 9, 0, 0), "2026-10-05T09:00:00Z"),
        (utc(2026, 10, 5, 9, 0, 0, 999_999), "2026-10-05T09:00:00Z"),
        (
            datetime(2026, 10, 5, 11, 0, 0, tzinfo=timezone(timedelta(hours=2))),
            "2026-10-05T09:00:00Z",
        ),
        (utc(5, 1, 2, 3, 4, 5), "0005-01-02T03:04:05Z"),
    ],
)
def test_formats_as_utc_to_the_second(value, expected):
    assert format_timestamp(value) == expected


def test_naive_datetimes_are_refused():
    with pytest.raises(ValueError):
        to_utc_second(datetime(2026, 10, 5, 9, 0, 0))


class Model(Schema):
    at: Timestamp
    maybe: Timestamp | None = None


def test_schema_type_parses_and_serializes():
    model = Model.model_validate({"at": "2026-10-05T11:00:00.75+02:00"})
    assert model.at == utc(2026, 10, 5, 9, 0, 0)
    assert model.model_dump() == {"at": "2026-10-05T09:00:00Z", "maybe": None}
    assert model.model_dump_json() == '{"at":"2026-10-05T09:00:00Z","maybe":null}'


@pytest.mark.parametrize("value", [1759654800, 1759654800.0, True, ["2026-10-05T09:00:00Z"], {}])
def test_schema_type_rejects_non_strings(value):
    with pytest.raises(pydantic.ValidationError) as excinfo:
        Model.model_validate({"at": value})
    error = excinfo.value.errors()[0]
    assert error["type"] == "timestamp"
    assert error["msg"] == "must be an RFC 3339 timestamp such as 2026-10-05T09:00:00Z"


def test_schema_type_rejects_null_when_required():
    with pytest.raises(pydantic.ValidationError):
        Model.model_validate({"at": None})


def test_schema_type_reports_the_specific_problem():
    with pytest.raises(pydantic.ValidationError) as excinfo:
        Model.model_validate({"at": "2026-10-05T09:00Z"})
    assert excinfo.value.errors()[0]["msg"] == "must include seconds"
