import re

import pytest
from django.test import Client

from cra_service.api import api
from tests.conftest import TOKEN
from tests.problems import assert_problem

pytestmark = pytest.mark.django_db


def _api_routes():
    """Every (method, path) the API serves, so new routes are covered automatically."""
    schema = api.get_openapi_schema(path_prefix="")
    for path, operations in schema["paths"].items():
        for method in operations:
            yield method.upper(), re.sub(r"\{[^}]+\}", "x", path)


PROTECTED = sorted(set(_api_routes()) - {("GET", "/health")}) + [
    ("POST", "/health"),  # only GET /health is public
    ("HEAD", "/health"),
    ("GET", "/no-such-path"),  # 401 outranks 404
    ("PUT", "/test/reset"),  # 401 outranks 405
    ("GET", "/docs"),
    ("GET", "/openapi.json"),
    ("GET", "/admin/"),
]

BAD_AUTHORIZATION = {
    "missing": None,
    "wrong token": f"Bearer {TOKEN}x",
    "token prefix": f"Bearer {TOKEN[:-1]}",
    "empty bearer": "Bearer ",
    "scheme only": "Bearer",
    "no scheme": TOKEN,
    "basic scheme": f"Basic {TOKEN}",
    "non-ascii": "Bearer tést-token",
}


def test_route_list_covers_test_controls():
    assert {("POST", "/test/reset"), ("GET", "/test/clock"), ("PUT", "/test/clock")} <= set(
        PROTECTED
    )
    assert ("DELETE", "/test/clock") in PROTECTED


@pytest.mark.parametrize("method,path", PROTECTED)
@pytest.mark.parametrize("authorization", BAD_AUTHORIZATION.values(), ids=BAD_AUTHORIZATION)
def test_protected_routes_reject_missing_or_wrong_token(method, path, authorization):
    headers = {"Authorization": authorization} if authorization is not None else {}
    response = Client(headers=headers).generic(method, path)
    if method == "HEAD":
        assert response.status_code == 401
        return
    assert_problem(response, 401, "Unauthorized")
    assert response["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize("method,path", sorted(set(_api_routes()) - {("GET", "/health")}))
def test_protected_routes_accept_the_token(authed, method, path):
    response = authed.generic(method, path, b'{"now": "2026-10-05T09:00:00Z"}', "application/json")
    assert response.status_code not in (401, 403)


def test_scheme_is_case_insensitive():
    response = Client(headers={"Authorization": f"bearer {TOKEN}"}).get("/test/clock")
    assert response.status_code == 200


def test_401_outranks_413():
    response = Client().put("/test/clock", b"x" * 70_000, content_type="application/json")
    assert_problem(response, 401, "Unauthorized")


def test_health_needs_no_token():
    response = Client().get("/health")
    assert response.status_code == 200


def test_health_ignores_a_wrong_token():
    response = Client(headers={"Authorization": "Bearer nope"}).get("/health")
    assert response.status_code == 200


@pytest.mark.parametrize("configured", ["", None])
def test_no_configured_token_rejects_everything(settings, configured):
    # Fail closed: an unset API_TOKEN must not turn "Bearer " into a valid token.
    settings.API_TOKEN = configured
    response = Client(headers={"Authorization": "Bearer "}).get("/test/clock")
    assert_problem(response, 401, "Unauthorized")
    assert Client().get("/health").status_code == 200
