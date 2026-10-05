import re

import pytest
from django.test import Client

from cra_service.api import api
from cra_service.middleware import CLIENT_ENVIRON_KEY
from cra_service.settings import env_api_tokens
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


CLIENT_TOKENS = {"team17": "team17-token", "team21": "team21-token", "staff": "staff-token"}


@pytest.fixture
def client_tokens(settings):
    settings.API_TOKENS = CLIENT_TOKENS


@pytest.mark.parametrize("name,token", CLIENT_TOKENS.items())
def test_each_client_token_works_and_records_the_client(client_tokens, name, token):
    response = Client(headers={"Authorization": f"Bearer {token}"}).get("/test/clock")
    assert response.status_code == 200
    assert response.wsgi_request.client_name == name
    assert response.wsgi_request.META[CLIENT_ENVIRON_KEY] == name


@pytest.mark.parametrize("token", [TOKEN, "team17-token2", "team17-toke", "default"])
def test_unknown_token_is_rejected(client_tokens, token):
    response = Client(headers={"Authorization": f"Bearer {token}"}).get("/test/clock")
    assert_problem(response, 401, "Unauthorized")
    assert response.wsgi_request.client_name is None
    assert CLIENT_ENVIRON_KEY not in response.wsgi_request.META


def test_health_records_no_client_without_a_token(client_tokens):
    response = Client().get("/health")
    assert response.status_code == 200
    assert response.wsgi_request.client_name is None
    assert CLIENT_ENVIRON_KEY not in response.wsgi_request.META


@pytest.mark.parametrize("configured", [{}, {"default": ""}], ids=["none", "empty"])
@pytest.mark.parametrize("method,path", PROTECTED)
@pytest.mark.parametrize("authorization", ["Bearer ", f"Bearer {TOKEN}"])
def test_no_configured_token_rejects_everything(settings, configured, method, path, authorization):
    # Fail closed: no tokens (or only empty ones) must not turn "Bearer " into a valid token.
    settings.API_TOKENS = configured
    response = Client(headers={"Authorization": authorization}).generic(method, path)
    assert response.status_code == 401
    assert Client(headers={"Authorization": authorization}).get("/health").status_code == 200


def test_tokens_come_from_api_token_variables():
    environ = {
        "API_TOKEN_TEAM17": "a",
        "API_TOKEN_TEAM21": " b\n",  # stripped: secrets created with `echo` end in a newline
        "API_TOKEN_STAFF": "",  # empty values are ignored
        "API_TOKEN_EMPTY": " \n",
        "API_TOKEN_": "no name",
        "API_TOKENS": "not a client",
        "OTHER": "c",
    }
    assert env_api_tokens(environ) == {"team17": "a", "team21": "b"}


def test_api_token_is_the_default_client():
    assert env_api_tokens({"API_TOKEN": "x\n", "API_TOKEN_LOCAL": "y"}) == {
        "default": "x",
        "local": "y",
    }
    assert env_api_tokens({"API_TOKEN": "x", "API_TOKEN_DEFAULT": "y"}) == {"default": "y"}
    assert env_api_tokens({"API_TOKEN": ""}) == {}
    assert env_api_tokens({}) == {}
