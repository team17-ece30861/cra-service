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


def assert_described(document: dict, path: str, method: str, response) -> None:
    """The response's status is documented for this operation, and its body matches the
    documented schema for its media type."""
    responses = document["paths"][path][method]["responses"]
    spec = responses.get(str(response.status_code)) or responses.get("default")
    assert spec, f"{method.upper()} {path} returned {response.status_code}, not described"
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


def test_system_setup_responses_are_described(authed, client, monkeypatch):
    def setup(body, c=authed):
        return _post(c, "/test/setup", body)

    assert_described(SYSTEM, "/test/setup", "post", setup({"session_id": "s1", "setup": {}}))
    assert_described(SYSTEM, "/test/setup", "post", setup({"session_id": "s1"}))  # 409
    assert_described(SYSTEM, "/test/setup", "post", setup({"session_id": ""}))  # 400
    assert_described(SYSTEM, "/test/setup", "post", setup({"session_id": "s2"}, client))  # 401
    big = authed.post("/test/setup", "x" * 70_000, content_type="application/json")
    assert big.status_code == 413
    assert_described(SYSTEM, "/test/setup", "post", big)

    from core.models import SystemSession

    def crash(**kwargs):
        raise RuntimeError("unavailable")

    monkeypatch.setattr(SystemSession.objects, "create", crash)
    crashed = setup({"session_id": "s3"})
    assert crashed.status_code == 500
    assert_described(SYSTEM, "/test/setup", "post", crashed)


def test_system_report_responses_are_described(authed, client):
    _post(authed, "/test/setup", {"session_id": "s1", "setup": {}})
    for response in (
        authed.get("/test/report", {"session_id": "s1"}),  # 200
        authed.get("/test/report", {"session_id": "nope"}),  # 404
        authed.get("/test/report"),  # 400
        client.get("/test/report", {"session_id": "s1"}),  # 401
    ):
        assert_described(SYSTEM, "/test/report", "get", response)


# --- tester: /tester/test/setup, /run, /report --------------------------------------


def test_tester_setup_responses_are_described(authed, client, allowed, monkeypatch):
    calls = {"status": 201}

    def call(target_url, method, path, body=None, *, timeout):
        if calls["status"] == 201:
            return 201, {"session_id": body["session_id"]}
        return calls["status"], {"message": "Warming up", "source": "unknown"}

    monkeypatch.setattr(runner, "call", call)
    assert_described(TESTER, "/test/setup", "post", _setup(authed))  # 201
    assert_described(TESTER, "/test/setup", "post", _setup(authed, "ftp://x"))  # 400
    assert_described(TESTER, "/test/setup", "post", _setup(client))  # 401
    calls["status"] = 503
    assert_described(TESTER, "/test/setup", "post", _setup(authed))  # forwarded


def test_tester_run_and_report_responses_are_described(
    authed, client, target, no_target, monkeypatch
):
    lines = "".join(f'{{"test": "{t}", "outcome": "passed"}}\n' for t in PLANNED)
    monkeypatch.setattr(runner, "_pytest", _fake_pytest(lines, 0))
    session_id = _setup(authed).json()["session_id"]
    body = {"session_id": session_id}
    report = "/tester/test/report"
    assert_described(TESTER, "/test/report", "get", authed.get(report, body))  # 409
    assert_described(TESTER, "/test/run", "post", _post(authed, "/tester/test/run", body))  # 200
    assert_described(TESTER, "/test/run", "post", _post(authed, "/tester/test/run", body))  # 409
    for response in (
        _post(authed, "/tester/test/run", {"session_id": "nope"}),  # 404
        _post(authed, "/tester/test/run", {}),  # 400
        _post(client, "/tester/test/run", body),  # 401
    ):
        assert_described(TESTER, "/test/run", "post", response)
    for response in (
        authed.get(report, body),  # 200
        authed.get(report, {"session_id": "nope"}),  # 404
        authed.get(report),  # 400
        client.get(report, body),  # 401
    ):
        assert_described(TESTER, "/test/report", "get", response)


def test_an_aborted_run_report_is_described(authed, target, no_target, monkeypatch):
    lines = '{"test": "t.py::test_a", "outcome": "passed"}\n'
    monkeypatch.setattr(runner, "_pytest", _fake_pytest(lines, "timeout"))
    session_id = _setup(authed).json()["session_id"]
    run = _post(authed, "/tester/test/run", {"session_id": session_id})
    assert run.status_code == 500
    assert_described(TESTER, "/test/run", "post", run)
    stored = authed.get("/tester/test/report", {"session_id": session_id})
    assert_described(TESTER, "/test/report", "get", stored)
    assert [r["outcome"] for r in stored.json()["results"]] == ["pass", "error", "skip", "skip"]


def test_a_tester_crash_report_is_described(authed, target, no_target, monkeypatch):
    def crash(session_id, target_url):
        raise RuntimeError("tester bug")

    monkeypatch.setattr(runner, "run_suite", crash)
    session_id = _setup(authed).json()["session_id"]
    assert_described(
        TESTER, "/test/run", "post", _post(authed, "/tester/test/run", {"session_id": session_id})
    )
    stored = authed.get("/tester/test/report", {"session_id": session_id})
    assert_described(TESTER, "/test/report", "get", stored)
