"""Operation reports must not promote auth checks or incomplete tests into delivery evidence."""

import json
import os
import subprocess
import sys
from copy import deepcopy
from types import SimpleNamespace

import pytest

from acceptance import conftest as hooks
from acceptance.client import ROOT, Contract, Response, Service
from acceptance.reporting import operation_statuses, render_operation_table

DOCUMENT = {
    "paths": {
        "/features": {
            "parameters": [],
            "post": {
                "operationId": "createFeature",
                "description": "REQ-08, REQ-12 and REQ-08.",
                "responses": {"200": {}, "201": {}, "400": {}, "401": {}},
            },
        }
    }
}


def check(
    expected_status=200, *, conforms=True, actual_status=None, path="/features", method="POST"
):
    return {
        "method": method,
        "path": path,
        "expected_status": expected_status,
        "actual_status": expected_status if actual_status is None else actual_status,
        "conforms": conforms,
    }


def row_for(checks=(), *, outcome="passed"):
    results = [{"outcome": outcome, "operation_checks": list(checks), "teardown_complete": True}]
    return operation_statuses(DOCUMENT, results)[0]


def test_no_observations_leave_every_declared_status_untested():
    row = operation_statuses(DOCUMENT, [])[0]
    assert row["implementation"] == "not_demonstrated"
    assert row["success"]["status"] == row["error"]["status"] == "not_tested"
    assert row["success"]["untested_statuses"] == [200, 201]
    assert row["error"]["untested_statuses"] == [400, 401]


def test_auth_only_does_not_demonstrate_implementation_or_success():
    row = row_for([check(401)])
    assert row["implementation"] == "not_demonstrated"
    assert row["success"]["status"] == "not_tested"
    assert row["error"]["status"] == "partial"
    assert row["error"]["passed_statuses"] == [401]
    assert row["error"]["untested_statuses"] == [400]


def test_success_is_partial_until_all_declared_success_statuses_are_checked():
    row = row_for([check(200)])
    assert row["implementation"] == "success_observed"
    assert row["success"]["status"] == "partial"
    assert row["success"]["passed_statuses"] == [200]
    assert row["success"]["untested_statuses"] == [201]


def test_all_explicit_statuses_can_pass_without_claiming_complete_feature_coverage():
    row = row_for([check(status) for status in [200, 201, 400, 401]])
    assert row["success"]["status"] == row["error"]["status"] == "passed"
    assert row["implementation"] == "success_observed"


@pytest.mark.parametrize("expected_status,actual_status", [(200, 404), (401, 200), (200, 200)])
def test_wrong_status_or_schema_fails_the_expected_response_category(
    expected_status, actual_status
):
    row = row_for(
        [check(expected_status, conforms=False, actual_status=actual_status)], outcome="failed"
    )
    category = "success" if expected_status == 200 else "error"
    assert row[category]["status"] == "failed"
    assert row[category]["failed_statuses"] == [expected_status]
    assert row["implementation"] == "not_demonstrated"


@pytest.mark.parametrize("outcome", ["failed", "skipped", "not_run"])
def test_schema_valid_response_in_nonpassing_test_is_inconclusive(outcome):
    row = row_for([check()], outcome=outcome)
    assert row["implementation"] == "inconclusive"
    assert row["success"]["status"] == "inconclusive"
    assert row["success"]["passed_statuses"] == []
    assert row["success"]["inconclusive_statuses"] == [200]
    assert row["success"]["untested_statuses"] == [201]


@pytest.mark.parametrize("completion", [{}, {"teardown_complete": False}])
def test_unfinished_teardown_never_establishes_passing_evidence(completion):
    results = [{"outcome": "passed", "operation_checks": [check()], **completion}]
    row = operation_statuses(DOCUMENT, results)[0]
    assert row["implementation"] == "inconclusive"
    assert row["success"]["passed_statuses"] == []


def test_later_success_does_not_hide_an_earlier_failed_check():
    row = row_for([check(conforms=False, actual_status=500), check()])
    assert row["success"]["status"] == "failed"
    assert row["success"]["failed_statuses"] == [200]
    assert row["success"]["checks"] == 2


def test_results_from_unrelated_operations_do_not_count():
    row = row_for([check(path="/other"), check(method="GET")])
    assert row["success"]["checks"] == row["error"]["checks"] == 0


def test_legacy_test_results_without_observations_are_not_guessed_from_their_names():
    row = operation_statuses(DOCUMENT, [{"test": "test_ac01", "outcome": "passed"}])[0]
    assert row["implementation"] == "not_demonstrated"


def test_requirements_are_deduplicated_and_path_parameters_are_not_operations():
    rows = operation_statuses(DOCUMENT, [])
    assert len(rows) == 1
    assert rows[0]["requirements"] == ["REQ-08", "REQ-12"]
    assert rows[0]["operation_id"] == "createFeature"


def test_real_contract_has_fourteen_operations_and_clock_requirement_from_spec():
    rows = operation_statuses(Contract().document, [])
    assert len(rows) == 14
    for method in ["GET", "PUT", "DELETE"]:
        row = next(row for row in rows if row["method"] == method and row["path"] == "/test/clock")
        assert row["requirements"] == ["REQ-16"]
    health = next(row for row in rows if row["path"] == "/health")
    assert health["requirements"] == []
    assert health["error"]["status"] == "not_defined"


def test_aggregation_does_not_mutate_contract_or_test_results():
    document = deepcopy(DOCUMENT)
    results = [{"outcome": "passed", "operation_checks": [check()]}]
    before = deepcopy((document, results))
    operation_statuses(document, results)
    assert (document, results) == before


def test_markdown_explains_partial_and_untested_evidence():
    table = render_operation_table([row_for([check(401)])])
    assert "POST /features" in table
    assert "REQ-08, REQ-12" in table
    assert "not demonstrated" in table
    assert "partial (passed: 401; untested: 400)" in table
    assert "not full feature coverage" in table


class FakeTransport:
    def __init__(self, response):
        self.response = response

    def send(self, *args, **kwargs):
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def test_service_records_only_safe_metadata_after_status_and_schema_validation():
    private = "reporter-secret@example.invalid"
    transport = FakeTransport(Response(200, "application/json", b'{"now":"2026-10-05T09:00:00Z"}'))
    service = Service(transport)
    assert service.expect("get", "/test/clock", 200, body={"reporter": private}, token=private) == {
        "now": "2026-10-05T09:00:00Z"
    }
    assert service.operation_checks == [check(path="/test/clock", method="GET")]
    assert private not in json.dumps(service.operation_checks)


@pytest.mark.parametrize(
    "response,exception,actual_status",
    [
        (Response(404, "application/problem+json", b"{}"), AssertionError, 404),
        (Response(200, "application/json", b"{}"), AssertionError, 200),
        (Response(200, "application/json", b"{bad"), ValueError, 200),
        (TimeoutError("private detail"), TimeoutError, None),
    ],
    ids=["wrong-status", "wrong-schema", "bad-json", "timeout"],
)
def test_service_preserves_failed_check_evidence(response, exception, actual_status):
    service = Service(FakeTransport(response))
    with pytest.raises(exception):
        service.expect("GET", "/test/clock", 200)
    assert service.operation_checks == [
        {
            "method": "GET",
            "path": "/test/clock",
            "expected_status": 200,
            "actual_status": actual_status,
            "conforms": False,
        }
    ]


def test_resource_identifiers_are_replaced_by_the_explicit_template_in_evidence():
    service = Service(
        FakeTransport(Response(404, "application/problem+json", b'{"title":"x","status":404}'))
    )
    service.expect("GET", "/tickets/private-id", 404, template="/tickets/{id}")
    assert service.operation_checks[0]["path"] == "/tickets/{id}"
    assert "private-id" not in json.dumps(service.operation_checks)


@pytest.fixture
def report_state(monkeypatch):
    monkeypatch.setattr(hooks, "STARTED", 1_792_800_000.0)
    monkeypatch.setattr(hooks, "RESULTS", {})


def test_teardown_failure_prevents_call_phase_success_from_becoming_passing_evidence(report_state):
    properties = [("operation_checks", [check()])]
    for phase, failed in [("setup", False), ("call", False), ("teardown", True)]:
        report = SimpleNamespace(
            nodeid="test_example",
            when=phase,
            duration=0.1,
            user_properties=properties,
            failed=failed,
            skipped=False,
            outcome="failed" if failed else "passed",
            longrepr=SimpleNamespace(reprcrash=SimpleNamespace(message="teardown failed")),
        )
        hooks.pytest_runtest_logreport(report)
    row = operation_statuses(DOCUMENT, hooks.RESULTS.values())[0]
    assert row["success"]["status"] == "inconclusive"


@pytest.mark.parametrize("exitstatus,label", [(0, "finished"), (1, "finished"), (2, "incomplete")])
def test_json_and_markdown_exports_include_all_operations_and_run_context(
    tmp_path, report_state, exitstatus, label
):
    options = {
        "--report": str(tmp_path / "nested/results.json"),
        "--operation-report": str(tmp_path / "nested/operations.md"),
        "--base-url": "https://synthetic.example.invalid",
        "--tested-version": "synthetic-only",
    }
    config = SimpleNamespace(getoption=options.get)
    hooks.pytest_sessionfinish(SimpleNamespace(config=config), exitstatus)
    report = json.loads((tmp_path / "nested/results.json").read_text(encoding="utf-8"))
    markdown = (tmp_path / "nested/operations.md").read_text(encoding="utf-8")
    assert len(report["operations"]) == 14
    assert report["exit_code"] == exitstatus
    assert report["tested_version_label"] == "synthetic-only"
    assert f"Run: {label}" in markdown
    assert "GET /health" in markdown
    assert "not tested" in markdown


def test_terminal_table_is_printed_without_requesting_output_files(report_state):
    lines = []
    terminal = SimpleNamespace(write_line=lines.append, write_sep=lambda *args: None)
    config = SimpleNamespace(getoption=lambda option: "synthetic-only")
    hooks.pytest_terminal_summary(terminal, 0, config)
    assert any("GET /health" in line for line in lines)
    assert any("not demonstrated" in line for line in lines)


def test_collect_only_clears_prior_session_state_and_writes_no_reports(tmp_path, report_state):
    options = {"--report": str(tmp_path / "unwanted.json"), "--operation-report": None}
    config = SimpleNamespace(option=SimpleNamespace(collectonly=True), getoption=options.get)
    hooks.RESULTS["stale-test"] = {"outcome": "passed"}
    hooks.pytest_sessionstart(SimpleNamespace(config=config))
    hooks.pytest_sessionfinish(SimpleNamespace(config=config), 0)
    assert hooks.STARTED is None
    assert hooks.RESULTS == {}
    assert not (tmp_path / "unwanted.json").exists()


@pytest.mark.parametrize("interrupted", [False, True], ids=["finished", "interrupted-teardown"])
def test_real_pytest_hooks_exclude_fixture_calls_and_withhold_failed_test_evidence(
    tmp_path, interrupted
):
    (tmp_path / "conftest.py").write_text(
        "import pytest\n"
        "from acceptance.client import Response, Service\n"
        "class FakeTransport:\n"
        "    def send(self, method, path, **kwargs):\n"
        '        if path == "/test/reset":\n'
        '            return Response(204, "", b"")\n'
        '        return Response(200, "application/json", b\'{"status":"ok"}\')\n'
        "@pytest.fixture\n"
        "def service():\n"
        "    instance = Service(FakeTransport())\n"
        '    instance.expect("POST", "/test/reset", 204)\n'
        "    return instance\n"
        "@pytest.fixture\n"
        "def interrupt_teardown():\n"
        "    yield\n"
        "    raise KeyboardInterrupt()\n",
        encoding="utf-8",
    )
    (tmp_path / "test_synthetic.py").write_text(
        "def test_interrupted(service, interrupt_teardown):\n"
        '    service.expect("GET", "/health", 200)\n'
        if interrupted
        else "import pytest\n"
        "def test_success(service):\n"
        '    service.expect("GET", "/health", 200)\n'
        "def test_semantic_failure(service):\n"
        '    service.expect("GET", "/health", 200)\n'
        '    assert False, "synthetic failure after schema validation"\n'
        "def test_skip(service):\n"
        '    pytest.skip("synthetic skip")\n',
        encoding="utf-8",
    )
    environment = {
        key: os.environ[key]
        for key in ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP")
        if key in os.environ
    }
    environment.update({"PYTHONPATH": str(ROOT), "CRA_API_TOKEN": "synthetic-only"})
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-c",
            str(ROOT / "acceptance/pytest.ini"),
            "-p",
            "acceptance.conftest",
            str(tmp_path / "test_synthetic.py"),
            "--base-url=https://synthetic.example.invalid",
            "--allow-reset",
            "--report=" + str(tmp_path / "report.json"),
            "--operation-report=" + str(tmp_path / "operations.md"),
            "-q",
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == (2 if interrupted else 1), completed.stdout + completed.stderr
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    if interrupted:
        assert report["results"][0]["teardown_complete"] is False
        assert report["exit_code"] == 2
    else:
        assert (report["passed"], report["failed"], report["skipped"]) == (1, 1, 1)
    health = next(row for row in report["operations"] if row["path"] == "/health")
    reset = next(row for row in report["operations"] if row["path"] == "/test/reset")
    assert health["success"]["status"] == "inconclusive"
    assert reset["implementation"] == "not_demonstrated"
    assert reset["success"]["checks"] == 0
    assert "Operation status (observed evidence only)" in completed.stdout
    assert "synthetic-only" not in json.dumps(report["operations"])
