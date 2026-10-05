import logging

import pytest
from django.test import Client

from core.models import FixedClock
from tests.conftest import TOKEN
from tests.problems import assert_problem

pytestmark = [pytest.mark.django_db, pytest.mark.urls("tests.urls")]

ACTOR = {"X-Actor": "Jane Analyst"}
VALID = b'{"now": "2026-10-05T09:00:00Z"}'


def _put_clock(client, body: bytes):
    return client.put("/test/clock", body, content_type="application/json")


# --- 400: schema errors (never ninja's default 422) ---------------------------


def test_schema_errors_are_400_not_422(authed):
    body = assert_problem(_put_clock(authed, b'{"now": 5}'), 400, "Invalid request")
    assert body["errors"][0]["field"] == "now"


@pytest.mark.parametrize(
    "raw",
    [
        b"{bad",
        b'{"now": "2026-10-05T09:00:00Z",}',
        b'{"now": NaN}',
        b'{"now": Infinity}',
        b'{"now": "\xff"}',  # not UTF-8
        b"\xef\xbb\xbf" + VALID,  # BOM
        b"[" * 60_000,  # nesting deep enough to exhaust the parser's recursion limit
        b'{"now": ' + b"9" * 5000 + b"}",  # over Python's int-digits limit
    ],
    ids=["truncated", "trailing comma", "NaN", "Infinity", "bad utf-8", "bom", "deep", "big int"],
)
def test_invalid_json_is_400(authed, raw):
    body = assert_problem(_put_clock(authed, raw), 400, "Invalid request")
    assert body["errors"] == [{"field": "body", "message": "must be valid JSON"}]


@pytest.mark.parametrize("raw", [b"[]", b'"now"', b"null", b"5", b"true"])
def test_non_object_body_is_400(authed, raw):
    body = assert_problem(_put_clock(authed, raw), 400, "Invalid request")
    assert body["errors"] == [{"field": "body", "message": "must be an object"}]


def test_missing_body_is_400(authed):
    body = assert_problem(_put_clock(authed, b""), 400, "Invalid request")
    assert body["errors"] == [{"field": "body", "message": "required"}]


def test_unknown_field_is_400(authed):
    raw = b'{"now": "2026-10-05T09:00:00Z", "speed": 2}'
    body = assert_problem(_put_clock(authed, raw), 400, "Invalid request")
    assert body["errors"] == [{"field": "speed", "message": "not allowed"}]


@pytest.mark.parametrize("route", ["/demo/things/open", "/demo/typed"])
@pytest.mark.parametrize("field", ["id", "state", "received_at"])
def test_system_set_field_is_400(authed, route, field):
    method = authed.patch if "things" in route else authed.post
    response = method(
        route, {"title": "t", field: "x"}, content_type="application/json", headers=ACTOR
    )
    body = assert_problem(response, 400, "Invalid request")
    assert body["errors"] == [{"field": field, "message": "not allowed"}]


@pytest.mark.parametrize("route", ["/demo/things/open", "/demo/typed"])
def test_errors_name_nested_fields(authed, route):
    # Manual (parse_body) and typed (ninja) validation report errors identically.
    method = authed.patch if "things" in route else authed.post
    payload = {
        "kind": "bogus",
        "product": {"manufacturer": "", "affected_versions": ["4.1", 7], "extra": 1},
    }
    response = method(route, payload, content_type="application/json", headers=ACTOR)
    body = assert_problem(response, 400, "Invalid request")
    assert sorted(body["errors"], key=lambda e: e["field"]) == [
        {"field": "kind", "message": "must be one of early_warning, notification"},
        {"field": "product.affected_versions[1]", "message": "must be a string"},
        {"field": "product.extra", "message": "not allowed"},
        {"field": "product.manufacturer", "message": "must not be empty"},
        {"field": "title", "message": "required"},
    ]


def test_invalid_query_parameter_is_400(authed):
    body = assert_problem(authed.get("/demo/search?kind=bogus"), 400, "Invalid request")
    assert body["errors"] == [
        {"field": "kind", "message": "must be one of early_warning, notification"}
    ]


def test_optional_body_may_be_absent(authed):
    response = authed.generic("POST", "/demo/things/open/notes", headers=ACTOR)
    assert response.status_code == 200
    assert response.json() == {"text": None}


# --- 413 ----------------------------------------------------------------------


def _padded(size: int) -> bytes:
    body = VALID[:-1] + b" " * (size - len(VALID)) + b"}"
    assert len(body) == size
    return body


def test_body_of_exactly_64_kib_is_accepted(authed):
    response = _put_clock(authed, _padded(65_536))
    assert response.status_code == 200


def test_body_over_64_kib_is_413(authed):
    assert_problem(_put_clock(authed, _padded(65_537)), 413, "Payload too large")


def test_body_over_djangos_upload_limit_is_413_not_400(authed):
    assert_problem(_put_clock(authed, b"x" * 3_000_000), 413, "Payload too large")


def test_413_applies_to_routes_without_a_body(authed):
    response = authed.post("/test/reset", b"x" * 65_537, content_type="application/json")
    assert_problem(response, 413, "Payload too large")


def test_oversized_body_changes_nothing(authed):
    big = b'{"now": "2030-01-01T00:00:00Z"' + b" " * 70_000 + b"}"
    _put_clock(authed, big)
    assert not FixedClock.objects.exists()


# --- 404 and 405 ----------------------------------------------------------------


def test_unknown_path_is_404(authed):
    assert_problem(authed.get("/no-such-path"), 404, "Not found")


def test_trailing_slash_is_404_not_a_redirect(authed):
    assert_problem(authed.get("/test/clock/"), 404, "Not found")


def test_unknown_path_is_404_in_debug_mode(authed, settings):
    settings.DEBUG = True
    body = assert_problem(authed.get("/no-such-path"), 404, "Not found")
    assert set(body) == {"title", "status"}


def test_invalid_path_parameter_is_404(authed):
    # e.g. an unknown report type in /tickets/{id}/reports/{type}
    assert_problem(authed.get("/demo/kinds/bogus"), 404, "Not found")
    assert authed.get("/demo/kinds/notification").status_code == 200


def test_wrong_method_is_405(authed):
    response = authed.put("/test/reset")
    assert_problem(response, 405, "Method not allowed")
    assert response["Allow"] == "POST"


def test_wrong_method_on_health_is_405(authed):
    assert_problem(authed.post("/health"), 405, "Method not allowed")


# --- 409 and 422 ----------------------------------------------------------------


def test_conflict_is_409(authed):
    response = authed.patch(
        "/demo/things/locked", {"title": "t"}, content_type="application/json", headers=ACTOR
    )
    body = assert_problem(response, 409, "Conflict")
    assert body["detail"] == "The thing is locked."


def test_rule_violation_is_422_with_errors(authed):
    response = authed.patch(
        "/demo/things/open",
        {"title": "breaks-rule"},
        content_type="application/json",
        headers=ACTOR,
    )
    body = assert_problem(response, 422, "Rule violation")
    assert body["errors"] == [{"field": "title", "message": "breaks a rule"}]


# --- Precedence: 401, 413, 404, 400, 409, 422 -----------------------------------

BIG = b"x" * 70_000


@pytest.mark.parametrize(
    "token,id,body,headers,expected",
    [
        (None, "missing", BIG, {}, 401),
        (TOKEN, "missing", BIG, {}, 413),
        (TOKEN, "missing", b"{bad", {}, 404),
        (TOKEN, "locked", b"{bad", ACTOR, 400),
        (TOKEN, "locked", b'{"title": "t"}', {}, 400),
        (TOKEN, "locked", b'{"title": "breaks-rule"}', ACTOR, 409),
        (TOKEN, "open", b'{"title": "breaks-rule"}', ACTOR, 422),
        (TOKEN, "open", b'{"title": "fine"}', ACTOR, 200),
    ],
)
def test_error_precedence(token, id, body, headers, expected):
    auth = {"Authorization": f"Bearer {token}"} if token else {}
    client = Client(headers=auth)
    response = client.patch(
        f"/demo/things/{id}", body, content_type="application/json", headers=headers
    )
    assert response.status_code == expected


def test_413_outranks_404(authed):
    response = authed.post("/no-such-path", BIG, content_type="application/json")
    assert_problem(response, 413, "Payload too large")


def test_404_outranks_invalid_json(authed):
    response = authed.post("/no-such-path", b"{bad", content_type="application/json")
    assert_problem(response, 404, "Not found")


# --- 500 and rollback -----------------------------------------------------------


@pytest.mark.parametrize("debug", [False, True])
def test_unhandled_exception_is_a_bare_500(authed, settings, caplog, debug):
    settings.DEBUG = debug
    with caplog.at_level(logging.ERROR):
        response = authed.post(
            "/demo/crash-after-write", {"contact": "jdoe@example.org"}, "application/json"
        )
    body = assert_problem(response, 500, "Internal server error")
    assert body == {"title": "Internal server error", "status": 500}
    assert "RuntimeError" in caplog.text  # logged for us...
    assert "jdoe@example.org" not in caplog.text  # ...without the message


@pytest.mark.parametrize("debug", [False, True])
def test_exception_outside_the_api_is_a_bare_500(settings, debug):
    settings.DEBUG = debug
    client = Client(headers={"Authorization": f"Bearer {TOKEN}"}, raise_request_exception=False)
    response = client.post("/django-crash", {"contact": "jdoe@example.org"}, "application/json")
    body = assert_problem(response, 500, "Internal server error")
    assert set(body) == {"title", "status"}
    assert b"jdoe" not in response.content


def test_disallowed_host_is_a_problem(authed):
    response = authed.get("/test/clock", headers={"Host": "evil.example"})
    assert_problem(response, 400, "Invalid request")


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("route", ["/demo/conflict-after-write", "/demo/crash-after-write"])
def test_failed_request_changes_nothing(authed, route):
    response = authed.post(route)
    assert response.status_code in (409, 500)
    assert not FixedClock.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_failed_request_outside_the_api_changes_nothing():
    # An exception Django itself turns into a 500 page is rolled back too.
    client = Client(headers={"Authorization": f"Bearer {TOKEN}"}, raise_request_exception=False)
    assert client.post("/django-crash").status_code == 500
    assert not FixedClock.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_successful_write_is_committed(authed):
    assert authed.put("/test/clock", VALID, "application/json").status_code == 200
    assert FixedClock.objects.exists()


def test_reads_do_not_open_a_transaction(django_assert_num_queries):
    # GET /health stays off the database entirely.
    with django_assert_num_queries(0):
        assert Client().get("/health").status_code == 200
