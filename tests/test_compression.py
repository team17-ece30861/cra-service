"""Gzip on API responses (cra_service/compression.py): compressed only when the client
asks, byte-identical once decompressed, and errors keep their status and shape."""

import gzip
import json

import pytest
from django.test import Client

from tests.conftest import TOKEN
from tests.problems import PROBLEM, assert_problem
from tests.test_errors import _padded, _put_clock

pytestmark = pytest.mark.django_db

ACTOR = {"X-Actor": "Jane Analyst"}
GZIP = {"Accept-Encoding": "gzip, deflate, br"}
TICKET = {
    "source": "external_researcher",
    "title": "Compressed listing",
    "description": "Enough text to make the list worth compressing. " * 4,
    "product": {"manufacturer": "Acme", "name": "Router OS", "affected_versions": ["4.1.0"]},
    "reporter": {"name": "Simulated Reporter", "contact": "reporter@example.invalid"},
}


def _client(**headers):
    return Client(headers={"Authorization": f"Bearer {TOKEN}", **headers})


def _decoded(response) -> bytes:
    if response.get("Content-Encoding") == "gzip":
        return gzip.decompress(response.content)
    return response.content


@pytest.fixture
def listing():
    plain = _client(**ACTOR)
    for _ in range(5):
        assert plain.post("/tickets", TICKET, content_type="application/json").status_code == 201


def test_list_is_compressed_when_asked_and_identical_once_decompressed(listing):
    plain = _client().get("/tickets")
    zipped = _client(**GZIP).get("/tickets")
    assert plain.status_code == zipped.status_code == 200
    assert "Content-Encoding" not in plain
    assert zipped["Content-Encoding"] == "gzip"
    assert zipped["Content-Type"] == plain["Content-Type"] == "application/json; charset=utf-8"
    assert int(zipped["Content-Length"]) == len(zipped.content) < len(plain.content)
    assert gzip.decompress(zipped.content) == plain.content
    assert "Accept-Encoding" in plain["Vary"] and "Accept-Encoding" in zipped["Vary"]


@pytest.mark.parametrize("accept", ["identity", "deflate, br", ""])
def test_nothing_is_compressed_unless_the_client_accepts_gzip(listing, accept):
    response = _client(**{"Accept-Encoding": accept}).get("/tickets")
    assert response.status_code == 200
    assert "Content-Encoding" not in response
    assert len(json.loads(response.content)) == 5


def test_large_problem_responses_stay_problems_when_compressed():
    body = {f"unknown_{i}": i for i in range(40)}
    response = _client(**ACTOR, **GZIP).post("/tickets", body, content_type="application/json")
    assert response.status_code == 400
    assert response["Content-Type"] == PROBLEM
    assert response["Content-Encoding"] == "gzip"
    problem = json.loads(gzip.decompress(response.content))
    assert problem["status"] == 400 and problem["errors"]


def test_413_is_unchanged_with_gzip():
    response = _put_clock(_client(**GZIP), _padded(65_537))
    assert response.status_code == 413
    assert response["Content-Type"] == PROBLEM
    assert json.loads(_decoded(response))["title"] == "Payload too large"


def test_401_is_unchanged_with_gzip():
    response = Client(headers=GZIP).get("/tickets")
    assert response.status_code == 401
    assert response["WWW-Authenticate"] == "Bearer"
    assert json.loads(_decoded(response))["status"] == 401


def test_small_responses_are_left_alone():
    response = _client(**GZIP).get("/health")
    assert "Content-Encoding" not in response
    assert response.json() == {"status": "ok"}


def test_uncompressed_problems_still_pass_the_usual_checks():
    assert_problem(_put_clock(_client(), _padded(65_537)), 413, "Payload too large")


def test_console_pages_are_never_compressed():
    response = Client(headers=GZIP).get("/console/sign-in")
    assert response.status_code == 200
    assert len(response.content) >= 200  # big enough that gzip would otherwise apply
    assert "Content-Encoding" not in response
    assert b"csrfmiddlewaretoken" in response.content
