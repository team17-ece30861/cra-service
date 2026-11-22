"""AC-13 failure diagnostics and CLI cleanup, using synthetic responses only."""

import io
import json
import sys
from http.client import HTTPException
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.error import URLError

import pytest

from acceptance import malformed
from acceptance.client import Contract, Response

SECRET = "synthetic-bearer-token-never-a-real-credential"


@pytest.fixture
def request_case():
    operation = "POST /tickets"
    return malformed.MalformedRequest(
        operation=operation,
        method="POST",
        path="/tickets",
        headers=(("Content-Type", "application/json"),),
        body=b"{}",
        violations=("body: missing required properties",),
        fault=json.dumps([operation, [json.dumps(["body", "missing"])]]),
    )


@pytest.mark.parametrize(
    "response",
    [
        Response(500, "text/plain", f"Authorization: Bearer {SECRET}".encode()),
        Response(500, "text/plain", ("x" * 1990 + SECRET).encode()),
        Response(400, SECRET, b"{}"),
        Response(400, malformed.PROBLEM, json.dumps({SECRET: SECRET}).encode()),
        Response(401, malformed.PROBLEM, json.dumps({"status": SECRET}).encode()),
        Response(413, malformed.PROBLEM, json.dumps({"detail": SECRET}).encode()),
    ],
    ids=["reflected-body", "body-boundary", "media-type", "schema", "401", "413"],
)
def test_target_values_never_enter_failure_exports(request_case, response):
    service = SimpleNamespace(contract=Contract())
    outcome = malformed.run(service, lambda *args: response, [request_case], {})
    summary = malformed.summarize([request_case], malformed.GenerationStats(), outcome, {}, {}, 0)
    console = io.StringIO()
    malformed.print_summary(summary, out=console)

    assert summary["failures"] and summary["requests_sent"] == 1
    assert summary["by_status"] == {str(response.status): 1}
    assert summary["data_unchanged"]
    assert SECRET not in repr(outcome)
    assert SECRET not in json.dumps(summary)
    assert SECRET not in console.getvalue()
    retained = summary["failures"][0]["response"]
    assert retained["status"] == response.status
    assert "body" not in retained


@pytest.mark.parametrize("exception", [OSError, URLError, HTTPException])
def test_transport_error_text_is_not_exported(request_case, exception):
    service = SimpleNamespace(contract=Contract())
    outcome = malformed.run(service, Mock(side_effect=exception(SECRET)), [request_case], {})
    summary = malformed.summarize([request_case], malformed.GenerationStats(), outcome, {}, {}, 0)
    assert summary["failures"]
    assert summary["by_status"] == {"None": 1}
    assert SECRET not in repr(outcome)
    assert SECRET not in json.dumps(summary)


def test_untrusted_problem_status_is_not_exported(request_case):
    contract = Contract()
    contract.validate = Mock(return_value={"status": SECRET})
    problems = malformed.check_response(
        contract, request_case, Response(400, malformed.PROBLEM, b"{}")
    )
    assert problems
    assert SECRET not in repr(problems)


def test_valid_problem_response_still_passes(request_case):
    response = Response(
        400,
        malformed.PROBLEM,
        json.dumps(
            {
                "title": "Bad Request",
                "status": 400,
                "errors": [{"field": "body", "message": "required fields missing"}],
            }
        ).encode(),
    )
    assert malformed.check_response(Contract(), request_case, response) == []


@pytest.fixture
def simulated_cli(monkeypatch, request_case):
    """Mock generation, target and corpus gate; exercise real CLI output and cleanup."""
    service = Mock()
    service.list.return_value = []
    summary = {
        "requests_sent": 500,
        "seconds": 0,
        "corpus_fingerprint": "simulated",
        "distinct_invalid_inputs": 500,
        "fault_categories": 1,
        "by_status": {"400": 500},
        "by_operation": {"POST /tickets": {"400": 500}},
        "server_errors": 0,
        "failures": [],
        "data_unchanged": True,
    }
    monkeypatch.setenv("CRA_API_TOKEN", SECRET)
    monkeypatch.setattr(malformed, "PYTHON", sys.version_info[:2])
    monkeypatch.setattr(malformed, "Service", lambda transport: service)
    monkeypatch.setattr(malformed, "generate", lambda: ([request_case], None))
    monkeypatch.setattr(malformed, "expected_corpus", lambda: None)
    monkeypatch.setattr(malformed, "seed_tickets", lambda service: {"received": "seed-id"})
    monkeypatch.setattr(malformed, "observable_state", lambda *args: {})
    monkeypatch.setattr(malformed, "run", lambda *args, **kwargs: {"seeds": {}})
    monkeypatch.setattr(malformed, "summarize", lambda *args: summary)
    return service


def assert_reset_and_release(service):
    assert service.expect.call_args_list == [
        (("POST", "/test/reset", 204), {"actor": None}),
        (("POST", "/test/reset", 204), {"actor": None}),
        (("DELETE", "/test/clock", 204), {"actor": None}),
    ]


def test_missing_output_directory_still_cleans_up(simulated_cli, tmp_path):
    with pytest.raises(FileNotFoundError):
        malformed.main(
            [
                "--base-url",
                "http://localhost",
                "--reset",
                "--out",
                str(tmp_path / "absent" / "report.json"),
            ]
        )
    assert_reset_and_release(simulated_cli)


@pytest.mark.parametrize(
    "write_error", [PermissionError("denied"), OSError("disk full"), TypeError("serialization")]
)
@pytest.mark.parametrize("cleanup_fails", [False, True])
def test_report_error_preserved_and_both_cleanup_steps_attempted(
    simulated_cli, monkeypatch, tmp_path, write_error, cleanup_fails, capsys
):
    if cleanup_fails:
        simulated_cli.expect.side_effect = [None, AssertionError(SECRET), OSError(SECRET)]
    monkeypatch.setattr(malformed.json, "dump", Mock(side_effect=write_error))

    with pytest.raises(type(write_error)) as caught:
        malformed.main(
            ["--base-url", "http://localhost", "--reset", "--out", str(tmp_path / "report.json")]
        )

    assert caught.value is write_error
    assert_reset_and_release(simulated_cli)
    captured = capsys.readouterr()
    assert SECRET not in captured.out + captured.err


@pytest.mark.parametrize("cleanup_fails", [False, True])
def test_cleanup_controls_exit_status(simulated_cli, tmp_path, cleanup_fails, capsys):
    if cleanup_fails:
        simulated_cli.expect.side_effect = [None, AssertionError(SECRET), None]
    output = tmp_path / "report.json"
    result = malformed.main(["--base-url", "http://localhost", "--reset", "--out", str(output)])
    assert result == int(cleanup_fails)
    assert_reset_and_release(simulated_cli)
    assert json.loads(output.read_text())["data_unchanged"]
    captured = capsys.readouterr()
    assert SECRET not in captured.out + captured.err


def test_no_reset_mode_does_not_reset_or_release_on_report_error(
    simulated_cli, monkeypatch, tmp_path
):
    monkeypatch.setattr(malformed.json, "dump", Mock(side_effect=OSError("disk full")))
    with pytest.raises(OSError):
        malformed.main(["--base-url", "http://localhost", "--out", str(tmp_path / "report.json")])
    simulated_cli.expect.assert_not_called()


def test_preflight_failure_hides_target_text(simulated_cli, capsys):
    simulated_cli.list.side_effect = AssertionError(SECRET)
    assert malformed.main(["--base-url", "http://localhost", "--reset"]) == 2
    simulated_cli.expect.assert_not_called()
    captured = capsys.readouterr()
    assert SECRET not in captured.out + captured.err
