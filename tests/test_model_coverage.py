import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from acceptance import model_coverage as coverage
from acceptance.cases import Phase3Checks
from acceptance.client import Response, Service

MAPPING = "https://example.invalid/design/team17-phase5-design-v1"
ALL_PLANNED = sorted({value for value in coverage.scenario_bindings().values() if value})
INTAKE = "A-01.intake"
INTAKE_TEST = coverage.scenario_bindings()[INTAKE]


def evidence(*scenarios, satisfied=True):
    return {
        "version": coverage.DESIGN_VERSION,
        "available": True,
        "events": [{"scenario": scenario, "satisfied": satisfied} for scenario in scenarios],
    }


def test_inventory_keeps_all_forty_four_requirements_and_unbound_gaps():
    document = coverage.manifest()
    assert len(document["requirements"]) == 44
    assert len({row["id"] for row in document["requirements"]}) == 44
    assert all(row["scenarios"] for row in document["requirements"])
    assert any(scenario["test"] is None for scenario in document["requirements"][-1]["scenarios"])
    measure = coverage.model_measure(evidence(), [], MAPPING)
    assert (measure["covered"], measure["total"]) == (0, 44)


@pytest.mark.parametrize("satisfied", [True, False])
def test_evaluation_is_not_a_pass_rate(satisfied):
    measure = coverage.model_measure(evidence(INTAKE, satisfied=satisfied), [INTAKE_TEST], MAPPING)
    assert (measure["covered"], measure["total"]) == (1, 44)
    assert coverage.DESIGN_VERSION in measure["basis"]
    assert MAPPING in measure["basis"]
    assert "not a pass rate" in measure["basis"]


def test_duplicate_events_do_not_inflate_counts_or_mutate_evidence():
    recorded = evidence(INTAKE, INTAKE, INTAKE)
    before = json.dumps(recorded)
    assert coverage.model_measure(recorded, ALL_PLANNED, MAPPING)["covered"] == 1
    assert json.dumps(recorded) == before


def test_all_four_parameterized_drafts_are_required():
    scenarios = [
        "C-01." + report
        for report in ("early_warning", "notification", "final_report", "user_advisory")
    ]
    partial = coverage.model_measure(evidence(*scenarios[:3]), ALL_PLANNED, MAPPING)
    complete = coverage.model_measure(evidence(*scenarios), ALL_PLANNED, MAPPING)
    assert (partial["covered"], partial["total"]) == (0, 44)
    assert (complete["covered"], complete["total"]) == (1, 44)


@pytest.mark.parametrize(
    "recorded",
    [
        None,
        {},
        {"version": "old", "available": True, "events": []},
        {"version": coverage.DESIGN_VERSION, "available": False, "events": []},
        {"version": coverage.DESIGN_VERSION, "available": True, "events": None},
    ],
)
def test_unavailable_or_legacy_evidence_is_not_guessed(recorded):
    measured = coverage.model_measure(recorded, ALL_PLANNED, MAPPING)
    assert measured["covered"] is measured["total"] is None


@pytest.mark.parametrize(
    "event",
    [
        {"scenario": "A-99.fake", "satisfied": True},
        {"scenario": INTAKE, "satisfied": 1},
        {"scenario": INTAKE, "satisfied": "true"},
        {"scenario": INTAKE, "satisfied": True, "body": "private"},
        {"scenario": "I-02.no_server_errors", "satisfied": True},
        [INTAKE, True],
    ],
)
def test_unknown_unbound_or_unsafe_events_are_unavailable(event):
    recorded = evidence()
    recorded["events"] = [event]
    measure = coverage.model_measure(recorded, ALL_PLANNED, MAPPING)
    assert measure["covered"] is measure["total"] is None
    assert "private" not in measure["basis"]


def test_a_test_not_in_the_current_plan_cannot_supply_evidence():
    measured = coverage.model_measure(evidence(INTAKE), [], MAPPING)
    assert measured["covered"] is measured["total"] is None


@pytest.mark.parametrize(
    "mapping",
    ["", None, "file:///private/mapping.md", "https://user:secret@example.invalid/map"],
)
def test_an_unpublished_or_unsafe_mapping_does_not_claim_a_measure(mapping):
    measured = coverage.model_measure(evidence(INTAKE), ALL_PLANNED, mapping)
    assert measured["covered"] is measured["total"] is None
    assert "secret" not in measured["basis"]


def test_recorder_keeps_a_failed_oracle_and_preserves_the_assertion():
    journal = coverage.ModelJournal()
    actual = False
    with coverage.record_model_test(INTAKE_TEST, journal) as recorder:
        with pytest.raises(AssertionError, match="oracle failed"):
            with coverage.model_scenario(INTAKE):
                assert actual, "oracle failed"
    assert recorder.evidence() == evidence(INTAKE, satisfied=False)
    assert journal.events == evidence(INTAKE, satisfied=False)["events"]
    assert coverage.ACTIVE_RECORDER.get() is None


@pytest.mark.parametrize("exception", [TimeoutError, KeyError, RuntimeError])
def test_non_oracle_failures_do_not_manufacture_evaluations(exception):
    journal = coverage.ModelJournal()
    with coverage.record_model_test(INTAKE_TEST, journal) as recorder:
        with pytest.raises(exception):
            with coverage.model_scenario(INTAKE):
                raise exception("no evaluable value")
    assert recorder.evidence()["events"] == []


def test_unknown_scenarios_raise_before_evaluating_the_block():
    with pytest.raises(ValueError, match="Unknown model scenario"):
        with coverage.model_scenario("A-01.not_in_the_manifest"):
            pytest.fail("must not execute")


@pytest.mark.parametrize("comparisons", [[], (), [1], ["true"], [None], True])
def test_empty_or_unevaluated_groups_cannot_claim_a_model_oracle(comparisons):
    journal = coverage.ModelJournal()
    with coverage.record_model_test(INTAKE_TEST, journal):
        with pytest.raises(ValueError, match="evaluated boolean"):
            with coverage.model_scenario(INTAKE, comparisons=comparisons):
                pytest.fail("must not execute")
    assert journal.available is False
    assert journal.events == []


def test_an_unrelated_or_local_ci_test_cannot_claim_a_remote_binding():
    journal = coverage.ModelJournal()
    with coverage.record_model_test("tests/test_phase3_api.py::TestLocalPhase3::test_x", journal):
        with coverage.model_scenario(INTAKE):
            assert True
    assert journal.available is False
    assert journal.events == []


def test_journal_preserves_evaluations_before_a_later_abort(tmp_path):
    path = tmp_path / "evaluations.jsonl"
    journal = coverage.ModelJournal(path)
    with coverage.record_model_test(INTAKE_TEST, journal):
        with coverage.model_scenario(INTAKE):
            assert True
    with path.open("a", encoding="utf-8") as output:
        output.write('{"kind":"evaluation","scena')
    recovered = coverage.read_model_journal(path)
    assert recovered == evidence(INTAKE)
    assert coverage.model_measure(recovered, ALL_PLANNED, MAPPING)["covered"] == 1


@pytest.mark.parametrize(
    "tail",
    ["not json\n", '{"kind":"unavailable"}\n', '{"kind":"evaluation","body":"secret"}\n'],
)
def test_corrupt_or_invalidated_journal_is_not_zero_coverage(tmp_path, tail):
    path = tmp_path / "evaluations.jsonl"
    coverage.ModelJournal(path)
    with path.open("a", encoding="utf-8") as output:
        output.write(tail)
    recovered = coverage.read_model_journal(path)
    measure = coverage.model_measure(recovered, ALL_PLANNED, MAPPING)
    assert measure["covered"] is measure["total"] is None


def test_missing_and_unwritable_journals_are_unavailable(tmp_path):
    assert coverage.read_model_journal(tmp_path / "missing")["available"] is False
    journal = coverage.ModelJournal(tmp_path / "missing-parent/journal")
    assert journal.available is False


@pytest.mark.parametrize(
    "value,expected",
    [
        ("https://TEAM17.example:443/system/", "https://team17.example/system"),
        ("https://team17.example/system2", "https://team17.example/system2"),
        ("http://localhost:8000/", "http://localhost:8000"),
        ("http://[::1]:8000/", "http://[::1]:8000"),
        ("https://team17.example:444/system", "https://team17.example:444/system"),
        ("https://user:token@team17.example/system", None),
        ("https://team17.example/system?token=secret", None),
        ("https://team17.example/system#other", None),
        ("https://team17.example:bad/system", None),
        ("ftp://team17.example/system", None),
    ],
)
def test_ownership_canonicalization_preserves_path_port_and_scheme(value, expected):
    assert coverage.canonical_base_url(value) == expected


def test_test_ids_only_normalize_the_known_acceptance_prefix():
    assert coverage.canonical_test("acceptance/" + INTAKE_TEST) == INTAKE_TEST
    absolute = str(Path(coverage.__file__).parent / INTAKE_TEST)
    assert coverage.canonical_test(absolute) == INTAKE_TEST
    assert coverage.canonical_test("unrelated/" + INTAKE_TEST) is None


@pytest.mark.parametrize("change", ["requirement", "scenario", "binding", "description"])
def test_manifest_rejects_silent_requirement_or_scenario_changes(tmp_path, monkeypatch, change):
    document = json.loads(coverage.MANIFEST_PATH.read_text(encoding="utf-8"))
    if change == "requirement":
        document["requirements"].pop()
    elif change == "scenario":
        document["requirements"][0]["scenarios"].append({"id": "A-01.extra", "test": None})
    elif change == "binding":
        document["requirements"][0]["scenarios"][0]["test"] = None
    else:
        document["requirements"][0]["description"] = "Changed scope"
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    coverage.manifest.cache_clear()
    try:
        with monkeypatch.context() as context:
            context.setattr(coverage, "MANIFEST_PATH", path)
            with pytest.raises(ValueError, match="inventory changed"):
                coverage.manifest()
    finally:
        coverage.manifest.cache_clear()


def test_current_checkpoint_blocks_have_oracles_and_no_target_calls():
    service_methods = {"expect", "send", "get", "create", "triage", "list", "fix_clock"}
    target_helpers = {
        "read_draft",
        "audit_log",
        "observable_state",
        "closure_state",
        "list_tickets",
    }
    blocks = []
    for path in Path(coverage.__file__).parent.glob("*.py"):
        source = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(source):
            if not isinstance(node, ast.With):
                continue
            if not any(
                isinstance(item.context_expr, ast.Call)
                and isinstance(item.context_expr.func, ast.Name)
                and item.context_expr.func.id == "model_scenario"
                for item in node.items
            ):
                continue
            blocks.append(node)
            assert any(isinstance(child, ast.Assert) for child in ast.walk(node))
            for statement in node.body:
                for child in ast.walk(statement):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Name):
                            assert child.func.id not in target_helpers
                        elif (
                            isinstance(child.func, ast.Attribute)
                            and isinstance(child.func.value, ast.Name)
                            and child.func.value.id in {"service", "transport"}
                        ):
                            assert child.func.attr not in service_methods
    assert len(blocks) > 30


def test_optimized_python_cannot_claim_assertions_that_were_removed():
    program = (
        "import json\n"
        "from acceptance.model_coverage import ModelJournal, model_scenario, record_model_test\n"
        "journal = ModelJournal()\n"
        f"with record_model_test({INTAKE_TEST!r}, journal):\n"
        f"    with model_scenario({INTAKE!r}):\n"
        "        assert False\n"
        "print(json.dumps([journal.available, journal.events]))\n"
    )
    environment = {
        key: os.environ[key] for key in ("PATH", "SYSTEMROOT", "WINDIR") if key in os.environ
    }
    environment["PYTHONPATH"] = str(Path(coverage.__file__).resolve().parents[1])
    completed = subprocess.run(
        [sys.executable, "-O", "-c", program],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert json.loads(completed.stdout) == [False, []]


@pytest.mark.parametrize("missing_state", [False, True])
def test_intake_evaluates_all_required_values_before_crediting_a_group(missing_state):
    seen = []

    class Ticket(dict):
        def __getitem__(self, key):
            ordinal = dict.__getitem__(self, "ordinal")
            seen.append((ordinal, key))
            return super().__getitem__(key)

    tickets = [
        Ticket(ordinal=number, id="duplicate", state="received", received_at="fixed", aware_at=None)
        for number in (0, 1)
    ]
    if missing_state:
        tickets[1].pop("state")

    class Intake:
        def create(self):
            return tickets.pop(0)

    journal = coverage.ModelJournal()
    with coverage.record_model_test(INTAKE_TEST, journal):
        with pytest.raises(KeyError if missing_state else AssertionError) as raised:
            Phase3Checks().test_ac01_intake_has_unique_ids_and_fixed_receipt_time(Intake())
    if not missing_state:
        assert str(raised.value).startswith("ticket ids are unique: not satisfied; ")
        assert "ticket 2 received_at: expected '2026-10-05T09:00:00Z', got 'fixed'" in str(
            raised.value
        )
    assert all((number, "state") in seen for number in (0, 1))
    if missing_state:
        assert journal.events == []
    else:
        assert all(
            (number, field) in seen for number in (0, 1) for field in ("received_at", "aware_at")
        )
        assert journal.events == [{"scenario": INTAKE, "satisfied": False}]


@pytest.mark.parametrize("status", [200, 400, 500, None])
def test_unauthorized_status_oracle_records_failures_but_not_unavailable_responses(status):
    test_id = (
        "test_phase3.py::TestRemotePhase3::"
        "test_ac15_every_protected_operation_rejects_unauthorized_requests[no-token-POST /tickets]"
    )

    class Transport:
        def send(self, *args, **kwargs):
            if status is None:
                raise TimeoutError("synthetic transport failure")
            return Response(status, "application/json", b"{}")

    service = Service(Transport())
    journal = coverage.ModelJournal()
    with coverage.record_model_test(test_id, journal):
        with pytest.raises(TimeoutError if status is None else AssertionError):
            Phase3Checks().test_ac15_every_protected_operation_rejects_unauthorized_requests(
                service, "POST", "/tickets", False, None
            )
    if status in (200, 400):
        assert journal.events == [{"scenario": "X-02.auth_0_no_token", "satisfied": False}]
    else:
        assert journal.events == []


def test_bad_first_obligation_does_not_skip_other_status_and_deadline_predicates():
    seen = []

    class Obligation(dict):
        def __getitem__(self, key):
            seen.append((dict.__getitem__(self, "report"), key))
            return super().__getitem__(key)

    reports = ("early_warning", "notification", "final_report")
    obligations = {
        report: Obligation(
            report=report, status="wrong" if index == 0 else "not_applicable", due_at=None
        )
        for index, report in enumerate(reports)
    }

    class ClosedTicket:
        def create(self):
            return {"id": "synthetic"}

        def triage(self, *args):
            return {"state": "closed", "resolution": "invalid", "obligations": obligations}

    test_id = (
        "test_phase3.py::TestRemotePhase3::"
        "test_ac05_closed_ticket_remains_readable_and_rejects_changes[invalid]"
    )
    journal = coverage.ModelJournal()
    with coverage.record_model_test(test_id, journal):
        with pytest.raises(AssertionError):
            Phase3Checks().test_ac05_closed_ticket_remains_readable_and_rejects_changes(
                ClosedTicket(), "invalid"
            )
    assert all((report, field) in seen for report in reports for field in ("status", "due_at"))
    assert journal.events == [{"scenario": "B-01.invalid", "satisfied": False}]


def test_precomputed_predicates_have_no_hidden_boolean_short_circuit():
    for path in Path(coverage.__file__).parent.glob("*.py"):
        source = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(source):
            if isinstance(node, ast.With) and any(
                isinstance(item.context_expr, ast.Call)
                and isinstance(item.context_expr.func, ast.Name)
                and item.context_expr.func.id == "model_scenario"
                for item in node.items
            ):
                for statement in node.body:
                    if isinstance(statement, ast.Assert):
                        assert not any(
                            isinstance(child, (ast.BoolOp, ast.GeneratorExp))
                            or isinstance(child, ast.Compare)
                            and len(child.ops) > 1
                            for child in ast.walk(statement.test)
                        )
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "model_checks"
                and node.func.attr in {"append", "equal", "true"}
            ):
                continue
            assert not any(isinstance(child, ast.BoolOp) for child in ast.walk(node))
            assert not any(
                isinstance(child, ast.Compare) and len(child.ops) > 1 for child in ast.walk(node)
            )


def test_failed_oracle_groups_name_each_failed_comparison_without_echoing_bodies():
    checks = coverage.OracleChecks()
    checks.equal("state", "triaged", "received")
    checks.equal("due_at", "2026-10-06T09:00:00Z", "2026-10-06T09:00:00Z")
    checks.equal(
        "ticket",
        {"title": "New", "reporter": {"contact": "private@example.invalid"}},
        {"title": "Old", "reporter": {"contact": "other@example.invalid"}},
    )
    checks.equal("audit", [1, 2], [1, 2, 3])
    checks.true("reporter details absent", False)
    assert checks.results == [False, True, False, False, False]
    assert checks.summary() == (
        "state: expected 'received', got 'triaged'; "
        "ticket: reporter differs; title expected 'Old', got 'New'; "
        "audit: expected 3 items, got 2; "
        "reporter details absent: not satisfied"
    )
    assert "example.invalid" not in checks.summary()
