"""docs/interface/tester.yaml and system.yaml, the OpenAPI descriptions of our tester and of
the system's course test endpoints, match what the service actually returns."""

from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from tester import runner
from tests import test_test_interface as base

PLANNED, _fake_pytest, _post, _setup = base.PLANNED, base._fake_pytest, base._post, base._setup
# The tester fixtures from the interface tests, reused here.
allowed, no_target, target = base.allowed, base.no_target, base.target

pytestmark = pytest.mark.django_db

ROOT = Path(__file__).resolve().parents[1]
TESTER = yaml.safe_load((ROOT / "docs/interface/tester.yaml").read_text(encoding="utf-8"))
SYSTEM = yaml.safe_load((ROOT / "docs/interface/system.yaml").read_text(encoding="utf-8"))
CONTRACT = yaml.safe_load((ROOT / "openapi.yaml").read_text(encoding="utf-8"))
SYSTEM_OWN_PATHS = {"/test/setup", "/test/report"}


def _pointer(document: dict, ref: str):
    node = document
    for part in ref.lstrip("#").removeprefix("/").split("/"):
        node = node[part.replace("~1", "/").replace("~0", "~")]
    return node


def _validator(document: dict, schema_ref: str) -> Draft202012Validator:
    registry = Registry().with_resource(
        "urn:doc", Resource.from_contents(document, default_specification=DRAFT202012)
    )
    return Draft202012Validator({"$ref": "urn:doc" + schema_ref}, registry=registry)


def assert_described(document, path, method, response, status, *, forwarded=False) -> None:
    """The response has the expected status, that status is documented for this
    operation (only a forwarded target error may fall back to `default`), and the body
    matches the documented schema for its media type."""
    assert response.status_code == status, response.content
    responses = document["paths"][path][method]["responses"]
    spec = responses.get(str(status))
    if forwarded:
        spec = responses["default"]
    assert spec, f"{method.upper()} {path} returned {status}, which isn't described"
    if "$ref" in spec:
        spec = _pointer(document, spec["$ref"])
    media_type = response["Content-Type"].split(";")[0]
    schema = spec["content"][media_type]["schema"]
    _validator(document, schema["$ref"]).validate(response.json())


# --- the documents themselves -------------------------------------------------------


def test_system_description_references_every_contract_path():
    contract_paths = set(CONTRACT["paths"])
    assert set(SYSTEM["paths"]) == contract_paths | SYSTEM_OWN_PATHS
    for path in contract_paths:
        ref = SYSTEM["paths"][path]["$ref"]
        file, pointer = ref.split("#")
        assert file == "../../openapi.yaml"
        assert _pointer(CONTRACT, pointer) is CONTRACT["paths"][path]


@pytest.mark.parametrize("document", [TESTER, SYSTEM], ids=["tester", "system"])
def test_examples_match_their_schemas(document):
    def examples(node):
        if isinstance(node, dict):
            if "schema" in node and "example" in node and "$ref" in node["schema"]:
                yield node["schema"]["$ref"], node["example"]
            for value in node.values():
                yield from examples(value)

    found = list(examples({k: v for k, v in document.items() if k != "components"}))
    found += list(examples(document["components"]["responses"]))
    assert found
    for schema_ref, example in found:
        _validator(document, schema_ref).validate(example)


# --- system: POST /test/setup, GET /test/report -------------------------------------


def _big(client, path):
    return client.post(path, "x" * 70_000, content_type="application/json")


def test_system_setup_responses_are_described(authed, client, monkeypatch):
    def check(response, status):
        assert_described(SYSTEM, "/test/setup", "post", response, status)

    check(_post(authed, "/test/setup", {"session_id": "s1", "setup": {}}), 201)
    check(_post(authed, "/test/setup", {"session_id": "s1"}), 409)
    check(_post(authed, "/test/setup", {"session_id": ""}), 400)
    check(_post(client, "/test/setup", {"session_id": "s2"}), 401)
    check(_big(authed, "/test/setup"), 413)

    from core.models import SystemSession

    def crash(**kwargs):
        raise RuntimeError("unavailable")

    monkeypatch.setattr(SystemSession.objects, "create", crash)
    check(_post(authed, "/test/setup", {"session_id": "s3"}), 500)


def test_system_report_responses_are_described(authed, client):
    _post(authed, "/test/setup", {"session_id": "s1", "setup": {}})
    for response, status in (
        (authed.get("/test/report", {"session_id": "s1"}), 200),
        (authed.get("/test/report", {"session_id": "nope"}), 404),
        (authed.get("/test/report"), 400),
        (client.get("/test/report", {"session_id": "s1"}), 401),
    ):
        assert_described(SYSTEM, "/test/report", "get", response, status)


# --- tester: /tester/test/setup, /run, /report --------------------------------------


def test_tester_setup_responses_are_described(authed, client, allowed, monkeypatch):
    answer = {}

    def call(target_url, method, path, body=None, *, timeout):
        if "raise" in answer:
            raise runner.CommunicationError("POST /test/setup failed: URLError")
        return answer.get("status", 201), answer.get("body", {"session_id": body["session_id"]})

    def check(response, status, **kwargs):
        assert_described(TESTER, "/test/setup", "post", response, status, **kwargs)

    monkeypatch.setattr(runner, "call", call)
    check(_setup(authed), 201)
    check(_setup(authed, "ftp://x"), 400)
    check(_setup(client), 401)
    check(_big(authed, "/tester/test/setup"), 413)
    answer.update(status=503, body={"message": "Warming up", "source": "unknown"})
    response = _setup(authed)
    check(response, 503, forwarded=True)
    assert response.json()["source"] == "unknown"  # the target's own source
    answer.update(status=201, body={})  # ready, but without the session ID
    response = _setup(authed)
    check(response, 500, forwarded=True)
    assert response.json()["source"] == "system"
    answer["raise"] = True
    response = _setup(authed)
    check(response, 500, forwarded=True)
    assert response.json()["source"] == "communication"


def test_tester_run_and_report_responses_are_described(
    authed, client, target, no_target, monkeypatch
):
    lines = "".join(f'{{"test": "{t}", "outcome": "passed"}}\n' for t in PLANNED)
    monkeypatch.setattr(runner, "_pytest", _fake_pytest(lines, 0))
    session_id = _setup(authed).json()["session_id"]
    body = {"session_id": session_id}
    report = "/tester/test/report"

    def run(response, status):
        assert_described(TESTER, "/test/run", "post", response, status)

    def lookup(response, status):
        assert_described(TESTER, "/test/report", "get", response, status)

    lookup(authed.get(report, body), 409)
    run(_post(authed, "/tester/test/run", body), 200)
    run(_post(authed, "/tester/test/run", body), 409)
    run(_post(authed, "/tester/test/run", {"session_id": "nope"}), 404)
    run(_post(authed, "/tester/test/run", {}), 400)
    run(_post(client, "/tester/test/run", body), 401)
    run(_big(authed, "/tester/test/run"), 413)
    lookup(authed.get(report, body), 200)
    lookup(authed.get(report, {"session_id": "nope"}), 404)
    lookup(authed.get(report), 400)
    lookup(client.get(report, body), 401)


def test_an_aborted_run_report_is_described(authed, target, no_target, monkeypatch):
    lines = '{"test": "t.py::test_a", "outcome": "passed"}\n'
    monkeypatch.setattr(runner, "_pytest", _fake_pytest(lines, "timeout"))
    session_id = _setup(authed).json()["session_id"]
    run = _post(authed, "/tester/test/run", {"session_id": session_id})
    assert_described(TESTER, "/test/run", "post", run, 500)
    stored = authed.get("/tester/test/report", {"session_id": session_id})
    assert_described(TESTER, "/test/report", "get", stored, 200)
    assert [r["outcome"] for r in stored.json()["results"]] == ["pass", "error", "skip", "skip"]


def test_a_tester_crash_report_is_described(authed, target, no_target, monkeypatch):
    def crash(session_id, target_url):
        raise RuntimeError("tester bug")

    monkeypatch.setattr(runner, "run_suite", crash)
    session_id = _setup(authed).json()["session_id"]
    run = _post(authed, "/tester/test/run", {"session_id": session_id})
    assert_described(TESTER, "/test/run", "post", run, 500)
    stored = authed.get("/tester/test/report", {"session_id": session_id})
    assert_described(TESTER, "/test/report", "get", stored, 200)
