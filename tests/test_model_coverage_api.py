import json
from copy import deepcopy

import pytest

from acceptance.client import Service
from acceptance.model_coverage import (
    DESIGN_VERSION,
    ModelJournal,
    model_scenario,
    record_model_test,
)
from acceptance.submission_cases import FIXED, SubmissionChecks
from tester import runner
from tests.test_interface_descriptions import TESTER, assert_described
from tests.test_phase3_api import DjangoTransport

pytestmark = pytest.mark.django_db

OWN = "https://shared.example/system17"
OTHER = "https://shared.example/system21"
INTAKE_TEST = (
    "test_phase3.py::TestRemotePhase3::test_ac01_intake_has_unique_ids_and_fixed_receipt_time"
)
MAPPING = "https://example.invalid/design/team17-phase5-design-v1"


@pytest.fixture
def configured(settings):
    settings.ALLOWED_HOSTS = ["shared.example", "testserver"]
    settings.TESTER_ALLOWED_HOSTS = ["shared.example"]
    settings.TESTER_OWN_SYSTEM_URLS = [OWN]
    settings.TESTER_MODEL_MAPPING_URL = MAPPING


def _fake_run(monkeypatch, *, outcome=0, emit=True, invalid=False, truncated_final=False):
    monkeypatch.setattr(runner, "planned_tests", lambda: [INTAKE_TEST])
    monkeypatch.setattr(
        runner, "_code_coverage", lambda *args: {"covered": None, "total": None, "basis": "fake"}
    )

    def run(*args, env=None, timeout):
        arguments = list(args)
        journal = ModelJournal(arguments[arguments.index("--model-progress") + 1])
        if emit:
            with record_model_test(INTAKE_TEST, journal):
                with model_scenario("A-01.intake"):
                    assert True
        if invalid:
            journal.invalidate()
        if truncated_final:
            report_path = arguments[arguments.index("--report") + 1]
            with open(report_path, "w", encoding="utf-8") as output:
                output.write('{"results":[')
        if outcome == "timeout":
            raise runner.subprocess.TimeoutExpired("pytest", timeout)
        report_path = arguments[arguments.index("--report") + 1]
        with open(report_path, "w", encoding="utf-8") as output:
            json.dump(
                {
                    "model_evidence_version": DESIGN_VERSION,
                    "model_evidence_available": journal.available,
                    "results": [{"test": INTAKE_TEST, "outcome": "passed"}],
                },
                output,
            )
        return runner.subprocess.CompletedProcess(arguments, outcome)

    monkeypatch.setattr(runner, "_pytest", run)


def test_only_explicit_same_team_base_gets_model_coverage(configured, monkeypatch):
    _fake_run(monkeypatch)
    own, aborted = runner.run_suite("own-run", OWN)
    other, other_abort = runner.run_suite("other-run", OTHER)
    assert aborted is other_abort is None
    assert own["coverage"]["model"] == {
        "covered": 1,
        "total": 44,
        "basis": f"Design {DESIGN_VERSION}; mapping: {MAPPING}; "
        "all required scenarios evaluated per requirement; not a pass rate",
    }
    assert set(other["coverage"]) == {"code", "component", "system"}


@pytest.mark.parametrize(
    "target,expected",
    [
        (OWN, True),
        (OWN + "/", True),
        ("https://SHARED.example:443/system17", True),
        (OTHER, False),
        (OWN + "-lookalike", False),
        ("http://shared.example/system17", False),
        ("https://shared.example:444/system17", False),
        ("https://user:secret@shared.example/system17", False),
    ],
)
def test_target_ownership_is_not_a_token_or_hostname_guess(configured, target, expected):
    assert runner.own_target(target) is expected


def test_unpublished_mapping_is_explicitly_unavailable(configured, settings, monkeypatch):
    settings.TESTER_MODEL_MAPPING_URL = ""
    _fake_run(monkeypatch)
    measured = runner.run_suite("local-only", OWN)[0]["coverage"]["model"]
    assert measured["covered"] is measured["total"] is None
    assert "mapping not yet published" in measured["basis"]


@pytest.mark.parametrize("emit,expected", [(False, 0), (True, 1)])
def test_abort_keeps_only_available_evaluations(configured, monkeypatch, emit, expected):
    _fake_run(monkeypatch, outcome="timeout", emit=emit)
    report, aborted = runner.run_suite("interrupted", OWN)
    assert aborted
    assert report["coverage"]["model"]["covered"] == expected
    assert report["coverage"]["model"]["total"] == 44


def test_corrupt_collector_is_not_reported_as_zero(configured, monkeypatch):
    _fake_run(monkeypatch, invalid=True)
    measured = runner.run_suite("unavailable", OWN)[0]["coverage"]["model"]
    assert measured["covered"] is measured["total"] is None


def test_an_abort_recovers_the_journal_when_the_final_report_is_truncated(configured, monkeypatch):
    _fake_run(monkeypatch, outcome="timeout", truncated_final=True)
    report, aborted = runner.run_suite("interrupted-final-write", OWN)
    assert aborted
    assert report["coverage"]["model"]["covered"] == 1
    assert report["coverage"]["model"]["total"] == 44


def test_failure_before_the_collector_starts_has_null_own_model(configured, monkeypatch):
    monkeypatch.setattr(runner, "planned_tests", lambda: [INTAKE_TEST])
    own = runner.failed_report("failed-own", OWN, "aborted")
    other = runner.failed_report("failed-other", OTHER, "aborted")
    assert own["coverage"]["model"]["covered"] is None
    assert own["coverage"]["model"]["total"] is None
    assert "model" not in other["coverage"]


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("report_type", ["early_warning", "notification", "final_report"])
def test_locking_checkpoint_detects_a_live_snapshot_after_an_edit(report_type):
    class UnlockedDraftService(Service):
        def __init__(self):
            super().__init__(DjangoTransport())
            self.edited = False

        def expect(self, method, path, status, **kwargs):
            result = super().expect(method, path, status, **kwargs)
            if method == "PATCH" and kwargs.get("body") == {
                "product": {"name": "Post-record edit"}
            }:
                self.edited = True
            if self.edited and method == "GET" and path.endswith("/reports/" + report_type):
                result = deepcopy(result)
                result["content"]["product"]["name"] = "Post-record edit"
            return result

    service = UnlockedDraftService()
    service.fix_clock(FIXED)
    test_id = (
        "test_submissions.py::TestRemoteSubmissions::"
        f"test_ac09_records_locked_content_and_one_audit_entry[{report_type}]"
    )
    journal = ModelJournal()
    with record_model_test(test_id, journal):
        with pytest.raises(AssertionError):
            SubmissionChecks().test_ac09_records_locked_content_and_one_audit_entry(
                service, report_type
            )
    assert service.edited is True
    assert journal.events[-1] == {"scenario": "C-03.locked_" + report_type, "satisfied": False}


def test_completed_and_stored_own_report_have_the_same_model(configured, monkeypatch, authed):
    _fake_run(monkeypatch)
    monkeypatch.setattr(
        runner,
        "call",
        lambda target, method, path, body, timeout: (201, {"session_id": body["session_id"]}),
    )
    setup = authed.post("/tester/test/setup", {"target_url": OWN}, content_type="application/json")
    assert setup.status_code == 201
    session = setup.json()["session_id"]
    completed = authed.post(
        "/tester/test/run", {"session_id": session}, content_type="application/json"
    )
    stored = authed.get("/tester/test/report", {"session_id": session})
    assert completed.status_code == stored.status_code == 200
    assert_described(TESTER, "/test/run", "post", completed, 200)
    assert_described(TESTER, "/test/report", "get", stored, 200)
    assert (
        "model" in TESTER["components"]["schemas"]["Report"]["properties"]["coverage"]["properties"]
    )
    assert stored.json() == completed.json()
    assert stored.json()["coverage"]["model"]["total"] == 44
    assert (
        authed.post(
            "/tester/test/run", {"session_id": session}, content_type="application/json"
        ).status_code
        == 409
    )
