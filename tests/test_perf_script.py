"""The AC-18 script's pure parts (acceptance/perf.py): percentiles, the fixed mix and
load profile, and determinism of the generated plan."""

import json
from collections import Counter
from datetime import UTC, datetime
from urllib.error import URLError

import pytest

from acceptance import perf
from acceptance.client import Response

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


class FakeService:
    """Just enough of the API for the load phase. lose[(method, suffix)] lists, per
    matching call in order, None (answer normally), "before" (drop the request
    before it reaches the service) or "after" (apply it, then drop the response)."""

    def __init__(self, lose=None):
        self.tickets = {}
        self.lose = {key: list(value) for key, value in (lose or {}).items()}
        self.calls = []

    def send(self, method, path, *, body=None, actor=None):
        self.calls.append((method, path))
        suffix = path.split("/")[-1] if path.count("/") > 2 else path
        plan = self.lose.get((method, suffix), [])
        mode = plan.pop(0) if plan else None
        if mode == "before":
            raise URLError("connection reset")
        response = self._handle(method, path, body)
        if mode == "after":
            raise URLError("connection reset")
        return response

    def _handle(self, method, path, body):
        parts = path.strip("/").split("/")
        if method == "POST" and path == "/tickets":
            ticket_id = f"t{len(self.tickets)}"
            self.tickets[ticket_id] = {
                "id": ticket_id,
                "title": body["title"],
                "state": "received",
                "resolution": None,
                "obligations": {r: {"submitted_at": None} for r in perf.RECORDED["resolved"]},
            }
            return self._json(201, self.tickets[ticket_id])
        if method == "GET" and path == "/tickets":
            return self._json(200, list(self.tickets.values()))
        ticket = self.tickets[parts[1]]
        if method == "GET":
            return self._json(200, ticket)
        if parts[-1] == "triage":
            if ticket["state"] != "received":
                return self._json(409, {"title": "Conflict", "status": 409})
            reportable = body["decision"] == "actively_exploited"
            ticket["state"] = "reportable" if reportable else "closed"
            ticket["resolution"] = None if reportable else body["decision"]
        elif parts[-1] == "submission":
            obligation = ticket["obligations"][parts[3]]
            if obligation["submitted_at"] is not None:
                return self._json(409, {"title": "Conflict", "status": 409})
            obligation["submitted_at"] = "2026-11-21T00:00:00Z"
        elif parts[-1] == "close":
            if ticket["state"] != "reportable":
                return self._json(409, {"title": "Conflict", "status": 409})
            ticket["state"], ticket["resolution"] = "closed", "resolved"
        return self._json(200, ticket)

    @staticmethod
    def _json(status, body):
        return Response(status, "application/json", json.dumps(body).encode())


def resolved_spec():
    return next(s for s in perf.build_load_specs(17, 100, BASE) if s["category"] == "resolved")


def load(service, spec):
    loader = perf.Loader(service, sleep=lambda seconds: None)
    ticket_id = perf.load_ticket(loader, spec)
    return loader, ticket_id


def test_lost_create_response_finds_the_stored_ticket_instead_of_a_duplicate():
    service = FakeService(lose={("POST", "/tickets"): ["after"]})
    loader, ticket_id = load(service, resolved_spec())
    assert len(service.tickets) == 1
    assert service.tickets[ticket_id]["state"] == "closed"
    assert [r["outcome"] for r in loader.retries][-1] == "found the first attempt's result"


def test_create_dropped_before_the_service_is_sent_again():
    service = FakeService(lose={("POST", "/tickets"): ["before"]})
    loader, _ = load(service, resolved_spec())
    assert len(service.tickets) == 1
    assert service.calls.count(("POST", "/tickets")) == 2
    assert len(loader.retries) == 1


@pytest.mark.parametrize("suffix", ["triage", "submission", "close"])
def test_lost_change_response_then_409_counts_as_done_after_checking(suffix):
    service = FakeService(lose={("POST", suffix): ["after"]})
    loader, ticket_id = load(service, resolved_spec())
    ticket = service.tickets[ticket_id]
    assert (ticket["state"], ticket["resolution"]) == ("closed", "resolved")
    assert all(o["submitted_at"] for o in ticket["obligations"].values())
    assert loader.retries[-1]["outcome"] == "409 on retry; confirmed already done"


def test_409_on_retry_without_the_change_having_happened_still_fails():
    service = FakeService(lose={("POST", "triage"): ["before"]})
    spec = resolved_spec()
    loader = perf.Loader(service, sleep=lambda seconds: None)
    ticket_id = loader.create(spec["body"])["id"]
    service.tickets[ticket_id]["state"] = "closed"  # someone else closed it meanwhile
    with pytest.raises(perf.SetupError, match="expected 200, got 409"):
        loader.change(
            ticket_id,
            "/triage",
            "/tickets/{id}/triage",
            spec["triage"],
            lambda ticket: ticket["state"] == "reportable",
        )


def test_load_gives_up_after_three_retries():
    service = FakeService(lose={("POST", "/tickets"): ["before"] * 4})
    with pytest.raises(perf.SetupError, match="no response after 4 attempts"):
        load(service, resolved_spec())
    assert service.calls.count(("POST", "/tickets")) == 4
    assert service.tickets == {}


def test_measured_requests_are_never_retried():
    class Dropping:
        calls = 0

        def send(self, *args, **kwargs):
            Dropping.calls += 1
            raise URLError("connection reset")

    plan = [{"op": "list", "number": 0}]
    results = perf.run_measured(Dropping(), plan, {}, BASE, stored=0)
    assert Dropping.calls == 1
    assert results[0]["ok"] is False and results[0]["status"] is None
    assert perf.report(results, warmup=[])["passed"] is False
