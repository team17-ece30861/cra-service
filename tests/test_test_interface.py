"""The course's cross-team testing interface: system /test/setup and /test/report,
and the tester under /tester. The tester's suite run and its calls to the target
are replaced with fakes; the real suite runs in acceptance/."""

import json

import pytest

from tester import runner

pytestmark = pytest.mark.django_db

TARGET = "https://team21.example"


def _post(client, path, body):
    return client.post(path, body, content_type="application/json")


def _assert_interface_error(response, status, source):
    assert response.status_code == status
    body = response.json()
    assert body["message"]
    assert body["source"] == source


# --- system: POST /test/setup, GET /test/report -----------------------------------


def test_setup_returns_the_session_id(authed):
    response = _post(authed, "/test/setup", {"session_id": "run-1", "setup": {}})
    assert response.status_code == 201
    assert response.json() == {"session_id": "run-1"}


def test_setup_without_setup_data_is_accepted(authed):
    assert _post(authed, "/test/setup", {"session_id": "run-1"}).status_code == 201


def test_setup_rejects_a_repeated_session_id(authed):
    _post(authed, "/test/setup", {"session_id": "run-1", "setup": {}})
    response = _post(authed, "/test/setup", {"session_id": "run-1", "setup": {}})
    _assert_interface_error(response, 409, "system")


@pytest.mark.parametrize(
    "body", [{}, {"session_id": ""}, {"session_id": "run-1", "extra": 1}, {"session_id": 5}]
)
def test_setup_rejects_invalid_requests(authed, body):
    _assert_interface_error(_post(authed, "/test/setup", body), 400, "system")


def test_setup_requires_a_token(client):
    assert _post(client, "/test/setup", {"session_id": "run-1"}).status_code == 401


def test_report_returns_unavailable_code_coverage(authed):
    _post(authed, "/test/setup", {"session_id": "run-1", "setup": {}})
    response = authed.get("/test/report", {"session_id": "run-1"})
    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == "run-1"
    code = body["coverage"]["code"]
    assert code["covered"] is None and code["total"] is None and code["basis"]


def test_report_for_an_unknown_session_is_404(authed):
    _assert_interface_error(authed.get("/test/report", {"session_id": "nope"}), 404, "system")


def test_report_without_a_session_id_is_400(authed):
    _assert_interface_error(authed.get("/test/report"), 400, "system")


def test_reset_keeps_sessions(authed):
    _post(authed, "/test/setup", {"session_id": "run-1", "setup": {}})
    assert authed.post("/test/reset").status_code == 204
    assert authed.get("/test/report", {"session_id": "run-1"}).status_code == 200


# --- tester: /tester/test/setup, /run, /report -------------------------------------


@pytest.fixture
def allowed(settings):
    settings.TESTER_ALLOWED_HOSTS = ["team21.example"]


@pytest.fixture
def target(monkeypatch, allowed):
    """A target system whose setup succeeds and echoes the session ID."""
    calls = []

    def call(target_url, method, path, body=None, *, timeout):
        calls.append((target_url, method, path, body))
        return 201, {"session_id": body["session_id"]}

    monkeypatch.setattr(runner, "call", call)
    return calls


@pytest.fixture
def suite(monkeypatch):
    """A suite run that passes one test and fails another."""
    runs = []

    def run_suite(session_id, target_url):
        runs.append(session_id)
        report = {
            "session_id": session_id,
            "target_url": target_url,
            "results": [
                {"test_id": "test_ac01", "outcome": "pass", "message": "Passed."},
                {"test_id": "test_ac02", "outcome": "fail", "message": "expected 400"},
            ],
            "coverage": {},
        }
        return report, None

    monkeypatch.setattr(runner, "run_suite", run_suite)
    return runs


def _setup(authed, url=TARGET):
    return _post(authed, "/tester/test/setup", {"target_url": url})


def test_tester_setup_prepares_the_target(authed, target):
    response = _setup(authed, TARGET + "/")
    assert response.status_code == 201
    session_id = response.json()["session_id"]
    assert session_id.startswith("run-")
    assert target == [(TARGET, "POST", "/test/setup", {"session_id": session_id, "setup": {}})]


@pytest.mark.parametrize(
    "url", ["ftp://team21.example", "https://team21.example?x=1", "https://u:p@team21.example"]
)
def test_tester_setup_rejects_invalid_urls(authed, target, url):
    _assert_interface_error(_setup(authed, url), 400, "tester")
    assert target == []


def test_tester_setup_rejects_unapproved_targets(authed, target):
    _assert_interface_error(_setup(authed, "https://169.254.169.254"), 400, "tester")
    assert target == []


def test_tester_setup_forwards_a_system_error(authed, allowed, monkeypatch):
    def call(*args, **kwargs):
        return 500, {"message": "Could not initialize", "source": "system"}

    monkeypatch.setattr(runner, "call", call)
    response = _setup(authed)
    _assert_interface_error(response, 500, "system")
    assert response.json()["message"] == "Could not initialize"


def test_tester_setup_reports_a_missing_setup_endpoint(authed, allowed, monkeypatch):
    monkeypatch.setattr(runner, "call", lambda *a, **k: (404, {"title": "Not found"}))
    _assert_interface_error(_setup(authed), 404, "system")


def test_tester_setup_reports_communication_failures(authed, allowed, monkeypatch):
    def call(*args, **kwargs):
        raise runner.CommunicationError("POST /test/setup failed: URLError")

    monkeypatch.setattr(runner, "call", call)
    _assert_interface_error(_setup(authed), 500, "communication")


def test_tester_runs_once_and_keeps_the_report(authed, target, suite):
    session_id = _setup(authed).json()["session_id"]
    before = authed.get("/tester/test/report", {"session_id": session_id})
    _assert_interface_error(before, 409, "tester")

    run = _post(authed, "/tester/test/run", {"session_id": session_id})
    assert run.status_code == 200
    assert run.json()["session_id"] == session_id
    assert [r["outcome"] for r in run.json()["results"]] == ["pass", "fail"]

    stored = authed.get("/tester/test/report", {"session_id": session_id})
    assert stored.status_code == 200
    assert stored.json() == run.json()

    again = _post(authed, "/tester/test/run", {"session_id": session_id})
    _assert_interface_error(again, 409, "tester")
    assert suite == [session_id]


def test_tester_run_for_an_unknown_session_is_404(authed, suite):
    _assert_interface_error(_post(authed, "/tester/test/run", {"session_id": "x"}), 404, "tester")


def test_invalid_run_request_does_not_use_the_session(authed, target, suite):
    session_id = _setup(authed).json()["session_id"]
    bad = _post(authed, "/tester/test/run", {"session_id": session_id, "extra": 1})
    _assert_interface_error(bad, 400, "tester")
    assert _post(authed, "/tester/test/run", {"session_id": session_id}).status_code == 200


def test_aborted_run_returns_500_and_keeps_the_report(authed, target, monkeypatch):
    def run_suite(session_id, target_url):
        report = {
            "session_id": session_id,
            "target_url": target_url,
            "results": [{"test_id": "t", "outcome": "skip", "message": "Not executed."}],
            "coverage": {},
        }
        return report, "The test suite did not finish within 480 seconds"

    monkeypatch.setattr(runner, "run_suite", run_suite)
    session_id = _setup(authed).json()["session_id"]
    _assert_interface_error(
        _post(authed, "/tester/test/run", {"session_id": session_id}), 500, "tester"
    )
    stored = authed.get("/tester/test/report", {"session_id": session_id})
    assert stored.status_code == 200
    assert stored.json()["results"][0]["outcome"] == "skip"


def test_tester_requires_a_token(client):
    assert _post(client, "/tester/test/setup", {"target_url": TARGET}).status_code == 401


# --- tester.runner ------------------------------------------------------------------


def test_results_map_suite_outcomes():
    assert runner._result("a", {"outcome": "passed"})["outcome"] == "pass"
    assert runner._result("a", {"outcome": "skipped"})["outcome"] == "skip"
    assert runner._result("a", None)["outcome"] == "skip"
    failed = runner._result("a", {"outcome": "failed", "message": "expected 201, got 400"})
    assert failed == {"test_id": "a", "outcome": "fail", "message": "expected 201, got 400"}
    timeout = runner._result("a", {"outcome": "failed", "message": "TimeoutError: timed out"})
    assert timeout["outcome"] == "error" and timeout["source"] == "communication"


def test_system_coverage_counts_executed_acceptance_criteria():
    results = [
        {"test_id": "cases.py::T::test_ac01_x", "outcome": "pass"},
        {"test_id": "cases.py::T::test_ac01_y", "outcome": "fail"},
        {"test_id": "cases.py::T::test_ac03_z[E1]", "outcome": "pass"},
        {"test_id": "cases.py::T::test_ac05_w", "outcome": "skip"},
    ]
    coverage = runner._system_coverage(results)
    assert (coverage["covered"], coverage["total"]) == (2, 19)


def test_tester_sends_our_own_token_only_to_this_service(settings):
    settings.ALLOWED_HOSTS = ["team17.example"]
    settings.API_TOKENS = {"team17": "own-token"}
    settings.TESTER_TARGET_TOKENS = {"team21.example": "their-token"}
    assert runner.target_token("https://team17.example") == "own-token"
    assert runner.target_token("https://team21.example") == "their-token"
    assert runner.target_token("https://elsewhere.example") is None


def test_tester_calls_send_an_actor_and_the_target_token(settings, monkeypatch):
    settings.TESTER_TARGET_TOKENS = {"team21.example": "their-token"}
    sent = []

    class FakeResponse:
        code = 201

        def read(self):
            return b'{"session_id": "run-1"}'

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def urlopen(request, timeout):
        sent.append(request)
        return FakeResponse()

    monkeypatch.setattr(runner, "urlopen", urlopen)
    status, body = runner.call(TARGET, "POST", "/test/setup", {"session_id": "run-1"}, timeout=5)
    assert (status, body) == (201, {"session_id": "run-1"})
    headers = dict(sent[0].header_items())
    assert headers["X-actor"] == runner.TESTER_ACTOR
    assert headers["Authorization"] == "Bearer their-token"


# --- error bodies outside the interface's own handlers -------------------------------


@pytest.mark.parametrize(
    ("method", "path", "source"),
    [
        ("post", "/test/setup", "system"),
        ("get", "/test/report", "system"),
        ("post", "/tester/test/setup", "tester"),
        ("post", "/tester/test/run", "tester"),
        ("get", "/tester/test/report", "tester"),
    ],
)
def test_interface_401s_carry_a_message_and_source(client, method, path, source):
    response = getattr(client, method)(path)
    _assert_interface_error(response, 401, source)
    assert response.json()["title"] == "Unauthorized"
    assert response["WWW-Authenticate"] == "Bearer"


def test_pod_test_controls_keep_the_plain_problem_body(client):
    body = client.post("/test/reset").json()
    assert body["status"] == 401
    assert "source" not in body and "message" not in body


def test_unknown_tester_routes_carry_a_message_and_source(authed):
    _assert_interface_error(authed.get("/tester/test/nothing"), 404, "tester")


def test_system_setup_crash_is_a_system_error(authed, monkeypatch):
    from core.models import SystemSession

    def crash(**kwargs):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(SystemSession.objects, "create", crash)
    response = _post(authed, "/test/setup", {"session_id": "run-x", "setup": {}})
    _assert_interface_error(response, 500, "system")
    assert "database unavailable" not in response.content.decode()
    # gunicorn sends no more than Content-Length bytes, so it must match the rewritten body.
    assert response["Content-Length"] == str(len(response.content))


def test_forwarded_errors_keep_their_own_message_and_source(authed, allowed, monkeypatch):
    monkeypatch.setattr(
        runner, "call", lambda *a, **k: (503, {"message": "Warming up", "source": "unknown"})
    )
    response = _setup(authed)
    _assert_interface_error(response, 503, "unknown")
    assert response.json()["message"] == "Warming up"


# --- results kept when the tester aborts ---------------------------------------------

PLANNED = ["t.py::test_a", "t.py::test_b", "t.py::test_c", "t.py::test_d"]


@pytest.fixture
def no_target(monkeypatch):
    monkeypatch.setattr(runner, "planned_tests", lambda: list(PLANNED))
    monkeypatch.setattr(
        runner, "_code_coverage", lambda *a: {"covered": None, "total": None, "basis": "fake"}
    )


def _fake_pytest(lines, outcome, final=None):
    """A suite run that writes these progress lines (and this final report text, if
    given), then times out or exits with the given code."""

    def fake(*args, env=None, timeout):
        args = list(args)
        with open(args[args.index("--progress") + 1], "w", encoding="utf-8") as file:
            file.write(lines)
        if final is not None:
            with open(args[args.index("--report") + 1], "w", encoding="utf-8") as file:
                file.write(final)
        if outcome == "timeout":
            raise runner.subprocess.TimeoutExpired("pytest", timeout)
        return runner.subprocess.CompletedProcess(args, outcome)

    return fake


def _final(*entries):
    return json.dumps({"results": [{"test": t, "outcome": o} for t, o in entries]})


def test_timeout_keeps_finished_results_and_marks_the_interrupted_test(no_target, monkeypatch):
    lines = (
        '{"test": "t.py::test_a", "outcome": "passed"}\n'
        '{"test": "t.py::test_b", "outcome": "failed", "message": "expected 409, got 200"}\n'
        '{"test": "t.py::test_c", "outc'  # cut off when the process was killed
    )
    monkeypatch.setattr(runner, "_pytest", _fake_pytest(lines, "timeout"))
    report, aborted = runner.run_suite("run-1", TARGET)
    assert aborted == f"The test suite did not finish within {runner.SUITE_TIMEOUT} seconds"
    results = report["results"]
    assert [r["test_id"] for r in results] == PLANNED
    assert [r["outcome"] for r in results] == ["pass", "fail", "error", "skip"]
    assert results[1]["message"] == "expected 409, got 200"
    assert results[2]["source"] == "tester"
    assert results[2]["message"] == f"Not evaluated: {aborted}."
    assert results[3]["message"] == f"Not executed: {aborted}."


def test_abort_before_any_result_marks_the_first_test_and_skips_the_rest(no_target, monkeypatch):
    monkeypatch.setattr(runner, "_pytest", _fake_pytest("", 3))
    report, aborted = runner.run_suite("run-1", TARGET)
    assert aborted == "The test suite stopped with exit code 3"
    assert [r["outcome"] for r in report["results"]] == ["error", "skip", "skip", "skip"]


def test_progress_lines_are_used_when_there_is_no_final_report(no_target, monkeypatch):
    lines = "".join(f'{{"test": "{t}", "outcome": "passed"}}\n' for t in PLANNED[:3])
    monkeypatch.setattr(runner, "_pytest", _fake_pytest(lines, 1))
    report, aborted = runner.run_suite("run-1", TARGET)
    assert aborted is None
    assert [r["outcome"] for r in report["results"]] == ["pass", "pass", "pass", "skip"]


def test_a_finished_run_uses_the_final_report(no_target, monkeypatch):
    final = _final(*[(t, "passed") for t in PLANNED[:3]], (PLANNED[3], "failed"))
    monkeypatch.setattr(runner, "_pytest", _fake_pytest("", 1, final))
    report, aborted = runner.run_suite("run-1", TARGET)
    assert aborted is None
    assert [r["outcome"] for r in report["results"]] == ["pass", "pass", "pass", "fail"]


def test_an_interrupted_suite_with_a_final_report_marks_its_unfinished_test(no_target, monkeypatch):
    final = _final((PLANNED[0], "passed"), (PLANNED[1], "not_run"))
    monkeypatch.setattr(runner, "_pytest", _fake_pytest("", 2, final))
    report, aborted = runner.run_suite("run-1", TARGET)
    assert aborted == "The test suite stopped with exit code 2"
    assert [r["outcome"] for r in report["results"]] == ["pass", "error", "skip", "skip"]


def test_a_test_skipped_by_the_suite_is_not_taken_for_the_interrupted_one(no_target, monkeypatch):
    lines = (
        f'{{"test": "{PLANNED[0]}", "outcome": "passed"}}\n'
        f'{{"test": "{PLANNED[1]}", "outcome": "skipped"}}\n'
    )
    monkeypatch.setattr(runner, "_pytest", _fake_pytest(lines, "timeout"))
    results = runner.run_suite("run-1", TARGET)[0]["results"]
    assert [r["outcome"] for r in results] == ["pass", "skip", "error", "skip"]
    assert results[1]["message"] == "Skipped by the suite."


def test_a_final_report_cut_off_mid_write_falls_back_to_progress(no_target, monkeypatch):
    lines = f'{{"test": "{PLANNED[0]}", "outcome": "passed"}}\n'
    monkeypatch.setattr(runner, "_pytest", _fake_pytest(lines, "timeout", '{"results": [{"te'))
    results = runner.run_suite("run-1", TARGET)[0]["results"]
    assert [r["outcome"] for r in results] == ["pass", "error", "skip", "skip"]


def test_a_tester_crash_still_reports_every_planned_test(authed, target, no_target, monkeypatch):
    def crash(session_id, target_url):
        raise RuntimeError("tester bug")

    monkeypatch.setattr(runner, "run_suite", crash)
    session_id = _setup(authed).json()["session_id"]
    _assert_interface_error(
        _post(authed, "/tester/test/run", {"session_id": session_id}), 500, "tester"
    )
    stored = authed.get("/tester/test/report", {"session_id": session_id}).json()
    assert [r["test_id"] for r in stored["results"]] == PLANNED
    assert [r["outcome"] for r in stored["results"]] == ["error", "skip", "skip", "skip"]
    assert stored["results"][0]["source"] == "tester"
    assert all(m["basis"] for m in stored["coverage"].values())
