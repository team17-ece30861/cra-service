"""The AC-18 script's pure parts (acceptance/perf.py): percentiles, the fixed mix and
load profile, and determinism of the generated plan."""

import gzip
import http.client
import json
import threading
import time
from collections import Counter
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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


def test_default_load_is_the_full_ticket_count_and_exact_limit_is_opt_in():
    mix = perf.MEASURED_MIX
    assert perf.load_size(1000, mix) == 1000  # AC-18's wording; the POSTs end at 1,010
    assert perf.load_size(1000, mix, exact_limit=True) == 990
    assert perf.load_size(1000, mix, exact_limit=True) + mix["create"] == 1000
    with pytest.raises(ValueError):
        perf.load_size(10, mix, exact_limit=True)
    sizes = perf.apportion(perf.LOAD_PROFILE, perf.load_size(1000, mix, exact_limit=True))
    perf.build_plan(17, mix, sizes)


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
    results = perf.run_measured(Dropping(), plan, {}, BASE)
    assert Dropping.calls == 1
    assert results[0]["ok"] is False and results[0]["status"] is None
    assert perf.report(results, warmup=[])["passed"] is False


def test_only_a_validated_1000_ticket_200_request_run_gets_pass_or_fail():
    args = {"validated": True, "tickets": 1000, "requests": 200}
    assert perf.verdict(True, **args) == "PASS"
    assert perf.verdict(False, **args) == "FAIL"
    off = {**args, "validated": False}
    assert perf.verdict(True, **off) == "NOT AC-18 EVIDENCE: validation off"
    assert perf.verdict(True, **{**args, "tickets": 300}) == "not an AC-18 run"
    assert perf.verdict(True, **{**args, "requests": 50}) == "not an AC-18 run"


def ticket_model():
    hour = perf.timedelta(hours=1)
    return {
        "received": perf.model_entry({}),
        "na": {**perf.model_entry({}), "state": "closed", "resolution": "invalid"},
        # Early warning due exactly at BASE: pending at BASE, overdue a second later.
        "boundary": {**perf.model_entry({}), "state": "reportable", "aware": BASE - 24 * hour},
        "late": {
            **perf.model_entry({}),
            "state": "reportable",
            "aware": BASE - 100 * hour,
            "subs": {"early_warning": BASE - 50 * hour},
        },
    }


def test_expected_ids_follow_model_b_and_allow_only_clock_boundary_doubt():
    model = ticket_model()
    later = BASE + perf.timedelta(seconds=30)
    assert perf.expected_ids(model, {"state": "reportable"}, BASE, later) == (
        {"boundary", "late"},
        {"boundary", "late"},
    )
    assert perf.expected_ids(model, {"obligation_status": "not_applicable"}, BASE, later)[0] == {
        "received",
        "na",
    }
    # Its notification is pending either way; only the early warning is in doubt.
    assert perf.expected_ids(model, {"obligation_status": "pending"}, BASE, later) == (
        {"boundary"},
        {"boundary"},
    )
    assert perf.expected_ids(model, {"obligation_status": "overdue"}, BASE, later) == (
        {"late"},
        {"boundary", "late"},
    )
    assert perf.expected_ids(model, {"obligation_status": "submitted_late"}, BASE, later) == (
        {"late"},
        {"late"},
    )
    assert perf.expected_ids(model, {"obligation_status": "awaiting_fix"}, BASE, BASE)[0] == {
        "boundary",
        "late",
    }


def test_final_report_deadline_uses_the_later_of_fix_and_awareness():
    aware = datetime(2026, 10, 5, 9, 0, 0, tzinfo=UTC)
    entry = {**perf.model_entry({}), "state": "reportable", "aware": aware}
    entry["fix"] = datetime(2026, 10, 20, 12, 0, 0, tzinfo=UTC)  # E4: due 2026-11-03T12:00Z
    assert "pending" in perf.obligation_statuses(entry, datetime(2026, 11, 3, 12, tzinfo=UTC))
    entry["subs"] = {"early_warning": aware, "notification": aware}
    late = datetime(2026, 11, 3, 12, 0, 1, tzinfo=UTC)
    assert perf.obligation_statuses(entry, late) == {"submitted", "overdue"}
    entry["fix"] = datetime(2026, 9, 28, tzinfo=UTC)  # E5: due 2026-10-19T09:00Z
    assert "overdue" in perf.obligation_statuses(entry, datetime(2026, 10, 19, 9, 1, tzinfo=UTC))


def test_filtered_list_missing_or_adding_a_ticket_is_a_failure():
    model = ticket_model()

    class Lists:
        def __init__(self, ids):
            self.ids = ids

        def send(self, *args, **kwargs):
            body = json.dumps([{"id": ticket_id} for ticket_id in self.ids]).encode()
            return Response(200, "application/json", body)

    plan = [{"op": "list_state", "query": {"state": "reportable"}, "number": 0}]
    for ids, ok in [
        (["boundary", "late"], True),
        (["late"], False),
        (["boundary", "late", "received"], False),
        (["late", "late", "boundary"], False),
    ]:
        [result] = perf.run_measured(Lists(ids), plan, {}, BASE, model)
        assert result["ok"] is ok, (ids, result["problem"])
    unfiltered = [{"op": "list", "number": 0}]
    [result] = perf.run_measured(Lists(["received", "na", "boundary"]), unfiltered, {}, BASE, model)
    assert "1 missing" in result["problem"]


def test_measured_changes_update_the_model_for_later_list_checks():
    model = ticket_model()
    ids = {("final_report", 0): "late"}
    perf.update_model(model, {"op": "close", "target": ("final_report", 0)}, ids, None, None)
    assert model["late"]["state"] == "closed"
    perf.update_model(model, {"op": "create"}, ids, {"title": "x"}, {"id": "new"})
    assert model["new"]["state"] == "received"


# ---------------------------------------------------------------- keep-alive transport


class _Handler(BaseHTTPRequestHandler):
    """HTTP/1.1 with keep-alive. The path picks the behavior: /gzip answers gzip-encoded
    when asked; /close says Connection: close; /quiet-close closes the connection after
    answering without saying so; /drop reads the request and closes without answering."""

    protocol_version = "HTTP/1.1"

    def setup(self):
        super().setup()
        self.server.connections += 1

    def do_GET(self):
        self.server.requests.append((self.path, dict(self.headers)))
        if self.path == "/drop":
            self.close_connection = True
            return
        body = json.dumps({"path": self.path, "pad": "x" * 500}).encode()
        gzipped = self.path == "/gzip" and "gzip" in self.headers.get("Accept-Encoding", "")
        if gzipped:
            body = gzip.compress(body)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if gzipped:
            self.send_header("Content-Encoding", "gzip")
        if self.path == "/close":
            self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        if self.path == "/quiet-close":
            self.close_connection = True

    def log_message(self, *args):
        pass


@pytest.fixture
def server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    httpd.connections, httpd.requests = 0, []
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd
    httpd.shutdown()
    httpd.server_close()


def _transport(server):
    return perf.KeepAliveTransport(f"http://127.0.0.1:{server.server_port}", "tok")


def test_keepalive_reuses_one_connection_and_decompresses_gzip(server):
    transport = _transport(server)
    for path in ("/a", "/gzip", "/b"):
        response = transport.send("GET", path, actor=None)
        assert response.status == 200
        assert json.loads(response.body)["path"] == path
    assert transport.connections_opened == server.connections == 1
    path, headers = server.requests[1]
    assert headers["Accept-Encoding"] == "gzip"
    assert headers["Authorization"] == "Bearer tok"


def test_server_connection_close_opens_a_new_connection_next_time(server):
    transport = _transport(server)
    transport.send("GET", "/close", actor=None)
    transport.send("GET", "/a", actor=None)
    assert transport.connections_opened == server.connections == 2
    assert len(server.requests) == 2


def test_idle_connection_closed_by_the_server_is_reopened_before_sending(server):
    transport = _transport(server)
    transport.send("GET", "/quiet-close", actor=None)
    time.sleep(0.2)  # let the server's close reach the client
    response = transport.send("GET", "/a", actor=None)
    assert response.status == 200
    assert transport.connections_opened == 2
    assert [path for path, _ in server.requests] == ["/quiet-close", "/a"]


def test_a_request_dropped_after_sending_fails_and_is_never_resent(server):
    transport = _transport(server)
    with pytest.raises(http.client.HTTPException):
        transport.send("GET", "/drop", actor=None)
    assert [path for path, _ in server.requests] == ["/drop"]
    assert transport.send("GET", "/a", actor=None).status == 200
    assert transport.connections_opened == 2


def test_each_thread_gets_its_own_connection(server):
    transport = _transport(server)
    transport.send("GET", "/a", actor=None)
    thread = threading.Thread(target=lambda: transport.send("GET", "/b", actor=None))
    thread.start()
    thread.join()
    transport.send("GET", "/c", actor=None)
    assert transport.connections_opened == server.connections == 2


def test_no_keepalive_flag_keeps_the_earlier_transport(monkeypatch):
    monkeypatch.setenv("CRA_API_TOKEN", "tok")
    assert perf.parse_args(["--base-url", "http://127.0.0.1:1"]).no_keepalive is False
    assert perf.parse_args(["--base-url", "http://127.0.0.1:1", "--no-keepalive"]).no_keepalive
