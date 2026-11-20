import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from acceptance.client import Contract, HTTPTransport, Service
from acceptance.model_coverage import DESIGN_VERSION, ModelJournal, record_model_test
from acceptance.reporting import operation_statuses, render_operation_table

RESULTS = {}
STARTED = None
PROGRESS = None  # --progress path: one JSON line per finished test, written as it finishes
MODEL_JOURNAL = None
MODEL_RECORDER = pytest.StashKey()


def pytest_addoption(parser):
    parser.addoption("--base-url", default=os.environ.get("CRA_BASE_URL"))
    parser.addoption(
        "--allow-reset", action="store_true", help="Permit clearing this test deployment"
    )
    parser.addoption(
        "--tested-version", default=os.environ.get("CRA_TESTED_VERSION", "unspecified")
    )
    parser.addoption("--report", default=None, help="Write a JSON result report")
    parser.addoption("--operation-report", default=None, help="Write a Markdown operation table")
    parser.addoption(
        "--model-progress", default=None, help="Write session model-evaluation evidence"
    )
    parser.addoption(
        "--progress",
        default=None,
        help="Append each finished test's result to this JSON Lines file as it finishes, "
        "so results survive if the run is stopped before the end",
    )


def pytest_sessionstart(session):
    global STARTED, PROGRESS, MODEL_JOURNAL
    config = session.config
    STARTED = None
    PROGRESS = None
    MODEL_JOURNAL = None
    RESULTS.clear()
    if config.option.collectonly:
        return
    if not config.getoption("--base-url"):
        raise pytest.UsageError("Provide --base-url or CRA_BASE_URL")
    if not os.environ.get("CRA_API_TOKEN"):
        raise pytest.UsageError("Set CRA_API_TOKEN in the environment")
    if not config.getoption("--allow-reset"):
        raise pytest.UsageError(
            "This suite resets all target data; "
            "pass --allow-reset for a coordinated test deployment"
        )
    try:
        HTTPTransport(config.getoption("--base-url"), os.environ["CRA_API_TOKEN"])
    except ValueError as error:
        raise pytest.UsageError(str(error)) from None
    STARTED = time.time()
    MODEL_JOURNAL = ModelJournal(config.getoption("--model-progress"))
    if config.getoption("--progress"):
        PROGRESS = Path(config.getoption("--progress"))
        PROGRESS.parent.mkdir(parents=True, exist_ok=True)


@pytest.fixture
def service(pytestconfig):
    return Service(HTTPTransport(pytestconfig.getoption("--base-url"), os.environ["CRA_API_TOKEN"]))


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    journal = MODEL_JOURNAL if MODEL_JOURNAL is not None else ModelJournal()
    with record_model_test(item.nodeid, journal) as recorder:
        item.stash[MODEL_RECORDER] = recorder
        yield


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and MODEL_RECORDER in item.stash:
        report.user_properties.append(("model_evidence", item.stash[MODEL_RECORDER].evidence()))
    service = item.funcargs.get("service")
    if service is None:
        return
    if report.when == "setup":
        service.operation_checks.clear()
    elif report.when == "call":
        report.user_properties.append(("operation_checks", service.operation_checks.copy()))


def pytest_runtest_logreport(report):
    entry = RESULTS.setdefault(
        report.nodeid,
        {"test": report.nodeid, "outcome": "not_run", "seconds": 0, "teardown_complete": False},
    )
    entry["seconds"] += report.duration
    if report.when == "teardown":
        entry["teardown_complete"] = True
    if report.when == "call":
        entry["operation_checks"] = dict(report.user_properties).get("operation_checks", [])
        entry["model_evidence"] = dict(report.user_properties).get("model_evidence")
    if report.failed and "message" not in entry:
        crash = getattr(report.longrepr, "reprcrash", None)
        entry["message"] = crash.message if crash else str(report.longrepr)[-500:]
    if report.failed or entry["outcome"] != "failed" and (report.when == "call" or report.skipped):
        entry["outcome"] = report.outcome
    # Written once the test's teardown ends, so a run stopped during a teardown reports
    # that test as interrupted even though its call had finished.
    if report.when == "teardown" and PROGRESS is not None:
        with PROGRESS.open("a", encoding="utf-8") as progress:
            progress.write(json.dumps(entry) + "\n")


def pytest_sessionfinish(session, exitstatus):
    destination = session.config.getoption("--report")
    operation_destination = session.config.getoption("--operation-report")
    if STARTED is None:
        return
    results = list(RESULTS.values())
    operations = operation_statuses(Contract().document, results)
    report = {
        "base_url": session.config.getoption("--base-url"),
        "tested_version_label": session.config.getoption("--tested-version"),
        "started_at": datetime.fromtimestamp(STARTED, UTC).isoformat(),
        "finished_at": datetime.fromtimestamp(time.time(), UTC).isoformat(),
        "exit_code": int(exitstatus),
        "tests_run": len(results),
        "passed": sum(result["outcome"] == "passed" for result in results),
        "failed": sum(result["outcome"] == "failed" for result in results),
        "skipped": sum(result["outcome"] == "skipped" for result in results),
        "code_coverage": "not measured by external HTTP tests",
        "results": results,
        "operations": operations,
        "model_evidence_version": DESIGN_VERSION,
        "model_evidence_available": MODEL_JOURNAL is not None and MODEL_JOURNAL.available,
    }
    if destination is not None:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if operation_destination is not None:
        path = Path(operation_destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_operation_report(session.config, exitstatus, operations), encoding="utf-8")


def _operation_report(config, exitstatus, operations):
    version = config.getoption("--tested-version")
    completed = "finished" if exitstatus in (0, 1) else "incomplete"
    return (
        f"# Operation status\n\nVersion label: {version}\n\n"
        f"Run: {completed}; pytest exit code {int(exitstatus)}.\n\n"
        + render_operation_table(operations)
        + "\n"
    )


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if STARTED is None:
        return
    operations = operation_statuses(Contract().document, RESULTS.values())
    terminalreporter.write_sep("=", "Operation status (observed evidence only)")
    for line in _operation_report(config, exitstatus, operations).splitlines():
        terminalreporter.write_line(line)
