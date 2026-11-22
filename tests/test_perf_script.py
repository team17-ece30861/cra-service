"""The AC-18 script's pure parts (acceptance/perf.py): percentiles, the fixed mix and
load profile, and determinism of the generated plan."""

from collections import Counter
from datetime import UTC, datetime

import pytest

from acceptance import perf

BASE = datetime(2026, 11, 21, 12, 0, 0, tzinfo=UTC)


def test_percentile_is_nearest_rank():
    values = [index / 1000 for index in range(1, 201)]  # 0.001 .. 0.200
    assert perf.percentile(values, 95) == 0.190  # the 190th of 200
    assert perf.percentile(values, 50) == 0.100
    assert perf.percentile(values, 99) == 0.198
    assert perf.percentile(values, 100) == 0.200
    assert perf.percentile(list(reversed(values)), 95) == 0.190


def test_percentile_small_samples_and_errors():
    assert perf.percentile([3.0], 95) == 3.0
    assert perf.percentile([1.0, 2.0], 50) == 1.0
    assert perf.percentile([1.0, 2.0], 51) == 2.0
    with pytest.raises(ValueError):
        perf.percentile([], 95)
    with pytest.raises(ValueError):
        perf.percentile([1.0], 0)


def test_default_mix_is_200_and_every_operation_has_an_expected_status():
    assert sum(perf.MEASURED_MIX.values()) == 200
    assert perf.apportion(perf.MEASURED_MIX, 200) == perf.MEASURED_MIX
    assert set(perf.MEASURED_MIX) == set(perf.OPERATIONS)


def test_apportion_always_sums_to_total():
    for total in (1, 7, 50, 199, 200, 201, 1000, 1003):
        counts = perf.apportion(perf.LOAD_PROFILE, total)
        assert sum(counts.values()) == total
    assert perf.apportion(perf.LOAD_PROFILE, 1000) == {
        "received_min": 150,
        "received_full": 150,
        "reportable": 250,
        "early_warning": 100,
        "notification": 100,
        "final_report": 50,
        "resolved": 50,
        "not_reportable": 150,
    }


def test_plan_is_deterministic_for_a_seed_and_follows_the_mix():
    sizes = perf.apportion(perf.LOAD_PROFILE, 1000)
    first = perf.build_plan(17, perf.MEASURED_MIX, sizes)
    assert first == perf.build_plan(17, perf.MEASURED_MIX, sizes)
    assert first != perf.build_plan(18, perf.MEASURED_MIX, sizes)
    assert Counter(step["op"] for step in first) == perf.MEASURED_MIX


def test_plan_never_reuses_a_ticket_across_mutations():
    sizes = perf.apportion(perf.LOAD_PROFILE, 1000)
    plan = perf.build_plan(17, perf.MEASURED_MIX, sizes)
    mutated = [step["target"] for step in plan if step["op"] in perf.MUTATION_POOLS]
    assert len(mutated) == len(set(mutated))
    for step in plan:
        if "target" in step:
            category, index = step["target"]
            assert 0 <= index < sizes[category]
        if step["op"] in perf.MUTATION_POOLS:
            assert step["target"][0] in perf.MUTATION_POOLS[step["op"]]
        if step["op"] == "draft":
            assert step["target"][0] in perf.REPORTABLE
        if step["op"] == "close":
            assert step["target"][0] == "final_report"


def test_plan_rejects_a_load_too_small_for_the_mix():
    with pytest.raises(ValueError, match="close"):
        perf.build_plan(17, perf.MEASURED_MIX, perf.apportion(perf.LOAD_PROFILE, 50))


def test_load_specs_are_deterministic_and_valid_in_time():
    specs = perf.build_load_specs(17, 1000, BASE)
    assert specs == perf.build_load_specs(17, 1000, BASE)
    assert Counter(spec["category"] for spec in specs) == perf.apportion(perf.LOAD_PROFILE, 1000)
    base = perf._iso(BASE)
    for spec in specs:
        triage = spec["triage"] or {}
        if "aware_at" in triage:
            assert triage["aware_at"] < base
            times = [triage["aware_at"]]
            times += [s["body"]["submitted_at"] for s in spec["submissions"]]
            assert times == sorted(times) and times[-1] <= base
        fix = spec["body"].get("fix")
        if fix:
            assert fix["available_at"] <= base
        assert [s["type"] for s in spec["submissions"]] == list(
            perf.RECORDED.get(spec["category"], ())
        )
        assert spec["close"] == (spec["category"] == "resolved")
        assert len(str(spec["body"])) < 16_000  # far under the 64 KB body limit


def test_report_counts_unexpected_statuses_as_failures_even_when_fast():
    results = [
        {
            "op": "get",
            "method": "GET",
            "path": "/tickets/{id}",
            "expected_status": 200,
            "status": 200,
            "seconds": 0.05,
            "ok": True,
            "problem": None,
        }
    ] * 199 + [
        {
            "op": "get",
            "method": "GET",
            "path": "/tickets/{id}",
            "expected_status": 200,
            "status": 500,
            "seconds": 0.001,
            "ok": False,
            "problem": "expected 200, got 500",
        }
    ]
    summary = perf.report(results, warmup=[])
    assert summary["overall"]["n"] == 200
    assert summary["unexpected"] == 1
    assert summary["passed"] is False
    assert summary["per_operation"]["get"]["n"] == 200


def test_report_fails_when_p95_is_over_one_second():
    def result(seconds):
        return {
            "op": "list",
            "method": "GET",
            "path": "/tickets",
            "expected_status": 200,
            "status": 200,
            "seconds": seconds,
            "ok": True,
            "problem": None,
        }

    passing = [result(0.2)] * 190 + [result(5.0)] * 10  # p95 is the 190th: 0.2 s
    failing = [result(0.2)] * 189 + [result(1.01)] * 11
    assert perf.report(passing, warmup=[])["passed"] is True
    assert perf.report(failing, warmup=[])["passed"] is False


def test_default_load_leaves_exactly_the_ticket_limit_after_the_measured_posts():
    mix = perf.MEASURED_MIX
    assert perf.load_size(1000, mix) == 990
    assert perf.load_size(1000, mix) + mix["create"] == 1000
    assert perf.load_size(1000, mix, exceed_limit=True) == 1000
    with pytest.raises(ValueError):
        perf.load_size(10, mix)
    perf.build_plan(17, mix, perf.apportion(perf.LOAD_PROFILE, perf.load_size(1000, mix)))
