import pytest

from tests.problems import assert_problem

pytestmark = [pytest.mark.django_db, pytest.mark.urls("tests.urls")]

URL = "/demo/things/open"
BODY = {"title": "A title"}


def _patch(client, actor=None, body=BODY):
    headers = {} if actor is None else {"X-Actor": actor}
    return client.patch(URL, body, content_type="application/json", headers=headers)


def test_missing_actor_is_400(authed):
    body = assert_problem(_patch(authed), 400, "Invalid request")
    assert body["errors"] == [{"field": "X-Actor", "message": "required"}]


@pytest.mark.parametrize("actor", ["", "   ", "\t"])
def test_empty_actor_is_400(authed, actor):
    body = assert_problem(_patch(authed, actor), 400, "Invalid request")
    assert body["errors"] == [{"field": "X-Actor", "message": "must not be empty"}]


def test_actor_over_200_characters_is_400(authed):
    body = assert_problem(_patch(authed, "a" * 201), 400, "Invalid request")
    assert body["errors"] == [{"field": "X-Actor", "message": "must be at most 200 characters"}]


def test_actor_of_200_characters_is_accepted(authed):
    response = _patch(authed, "a" * 200)
    assert response.status_code == 200
    assert response.json()["actor"] == "a" * 200


def test_actor_is_passed_to_the_view(authed):
    response = _patch(authed, " Jane Analyst ")
    assert response.status_code == 200
    assert response.json()["actor"] == "Jane Analyst"


def test_header_name_is_case_insensitive(authed):
    response = authed.patch(URL, BODY, content_type="application/json", headers={"x-actor": "j"})
    assert response.status_code == 200


def test_actor_checked_on_routes_without_a_body(authed):
    response = authed.generic("POST", "/demo/things/open/notes")
    body = assert_problem(response, 400, "Invalid request")
    assert body["errors"] == [{"field": "X-Actor", "message": "required"}]


@pytest.mark.parametrize(
    "method,path",
    [
        ("POST", "/test/reset"),
        ("PUT", "/test/clock"),
        ("DELETE", "/test/clock"),
        ("GET", "/test/clock"),
    ],
)
def test_test_controls_do_not_require_actor(authed, method, path):
    response = authed.generic(
        method, path, b'{"now": "2026-10-05T09:00:00Z"}', content_type="application/json"
    )
    assert response.status_code in (200, 204)
