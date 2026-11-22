"""The deployed tester's run rules (docs/plan.md, task 5.8): one run at a time, across
both gunicorn workers; recovery of a run cut off by a restart; and cleaning up the
target after each run (LIM-13)."""

import json
import threading
import time
from datetime import timedelta

import pytest
from django.db import connection
from django.db.models.functions import Now
from django.test import Client

from tester import runner, sessions
from tester.api import ANOTHER_RUN
from tester.models import TesterSession as Session
from tests import test_interface_descriptions as described
from tests import test_test_interface as base
from tests.conftest import TOKEN

PLANNED, TARGET, _post, _setup = base.PLANNED, base.TARGET, base._post, base._setup
_assert_interface_error = base._assert_interface_error
# Fixtures from the interface tests, reused here.
allowed, no_target, suite, target = base.allowed, base.no_target, base.suite, base.target

CLEANUP = [("DELETE", "/test/clock", None), ("POST", "/test/reset", None)]


def _run(client, session_id):
    return _post(client, "/tester/test/run", {"session_id": session_id})


def _report(client, session_id):
    return client.get("/tester/test/report", {"session_id": session_id})


def _calls(target):
    return [(method, path, body) for _, method, path, body in target]


def _running(session_id, *, heartbeat_age=0, run_age=0, planned=None, progress=None):
    """A session that started running `run_age` seconds ago and last beat
    `heartbeat_age` seconds ago (None: never)."""
    Session.objects.create(
        session_id=session_id,
        target_url=TARGET,
        created_at="2026-11-22T00:00:00Z",
        state="running",
        started_at=Now() - timedelta(seconds=run_age),
        heartbeat_at=None if heartbeat_age is None else Now() - timedelta(seconds=heartbeat_age),
        planned=planned,
        progress=progress,
    )


# --- LIM-13: the target is cleaned up after every run -------------------------------


@pytest.mark.django_db
def test_a_run_releases_the_clock_then_resets_the_target(authed, target, suite):
    session_id = _setup(authed).json()["session_id"]
    assert _run(authed, session_id).status_code == 200
    assert _calls(target)[1:] == CLEANUP


@pytest.mark.django_db
def test_cleanup_comes_after_the_suite_and_the_coverage_read(authed, allowed, monkeypatch):
    order = []

    def call(target_url, method, path, body=None, *, timeout):
        order.append((method, path.split("?")[0]))
        if path == "/test/setup":
            return 201, {"session_id": body["session_id"]}
        if path.startswith("/test/report"):
            return 200, {"coverage": {"code": {"covered": 1, "total": 2, "basis": "lines"}}}
        return 204, {}

    def fake_pytest(*args, env=None, timeout):
        order.append(("suite",))
        return runner.subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(runner, "call", call)
    monkeypatch.setattr(runner, "planned_tests", lambda: list(PLANNED))
    monkeypatch.setattr(runner, "_pytest", fake_pytest)
    session_id = _setup(authed).json()["session_id"]
    assert _run(authed, session_id).status_code == 200
    assert order == [
        ("POST", "/test/setup"),
        ("suite",),
        ("GET", "/test/report"),
        ("DELETE", "/test/clock"),
        ("POST", "/test/reset"),
    ]


@pytest.mark.django_db
def test_a_cleanup_failure_changes_nothing(authed, allowed, suite, monkeypatch, caplog):
    def call(target_url, method, path, body=None, *, timeout):
        if path == "/test/setup":
            return 201, {"session_id": body["session_id"]}
        if path == "/test/clock":
            raise runner.CommunicationError("DELETE /test/clock failed: URLError")
        return 500, {}

    monkeypatch.setattr(runner, "call", call)
    session_id = _setup(authed).json()["session_id"]
    run = _run(authed, session_id)
    assert run.status_code == 200
    assert [r["outcome"] for r in run.json()["results"]] == ["pass", "fail"]
    assert set(run.json()) == {"session_id", "target_url", "results", "coverage"}
    assert _report(authed, session_id).json() == run.json()
    assert "DELETE /test/clock failed: URLError; POST /test/reset returned 500" in caplog.text


def test_clean_up_target_reports_each_problem(monkeypatch):
    def call(target_url, method, path, body=None, *, timeout):
        assert timeout == runner.CLEANUP_TIMEOUT
        if method == "DELETE":
            raise RuntimeError("bug")
        return 404, {}

    monkeypatch.setattr(runner, "call", call)
    assert runner.clean_up_target(TARGET, "run-1") == [
        "DELETE /test/clock failed: RuntimeError",
        "POST /test/reset returned 404",
    ]


@pytest.mark.django_db
def test_an_aborted_run_still_cleans_up(authed, target, no_target, monkeypatch):
    monkeypatch.setattr(runner, "_pytest", base._fake_pytest("", "timeout"))
    session_id = _setup(authed).json()["session_id"]
    _assert_interface_error(_run(authed, session_id), 500, "tester")
    assert _calls(target)[-2:] == CLEANUP


@pytest.mark.django_db
def test_a_tester_crash_still_cleans_up(authed, target, no_target, monkeypatch):
    def crash(session_id, target_url, **kwargs):
        raise RuntimeError("tester bug")

    monkeypatch.setattr(runner, "run_suite", crash)
    session_id = _setup(authed).json()["session_id"]
    _assert_interface_error(_run(authed, session_id), 500, "tester")
    assert _calls(target)[1:] == CLEANUP


# --- one run at a time ---------------------------------------------------------------


@pytest.mark.django_db
def test_a_live_run_blocks_other_runs_and_setups(authed, target, suite):
    session_id = _setup(authed).json()["session_id"]
    _running("run-live", heartbeat_age=5, run_age=600)
    response = _run(authed, session_id)
    _assert_interface_error(response, 409, "tester")
    assert response.json()["message"] == ANOTHER_RUN
    described.assert_described(described.TESTER, "/test/run", "post", response, 409)
    response = _setup(authed)
    _assert_interface_error(response, 409, "tester")
    assert response.json()["message"] == ANOTHER_RUN
    described.assert_described(described.TESTER, "/test/setup", "post", response, 409)
    assert len(target) == 1  # the blocked setup never reached the target
    assert suite == []
    assert Session.objects.get(pk=session_id).state == "ready"  # still runnable
    _assert_interface_error(_report(authed, "run-live"), 409, "tester")


@pytest.mark.django_db
def test_errors_keep_their_precedence_while_a_run_is_live(authed, target, suite):
    _running("run-live", heartbeat_age=5)
    _assert_interface_error(_post(authed, "/tester/test/run", {}), 400, "tester")
    _assert_interface_error(_run(authed, "nope"), 404, "tester")
    _assert_interface_error(_setup(authed, "ftp://x"), 400, "tester")


def _in_thread(work):
    """Runs work() in a thread with its own database connection, like another worker."""
    result = {}

    def target():
        try:
            result["value"] = work()
        finally:
            connection.close()

    thread = threading.Thread(target=target)
    thread.start()
    return thread, result


@pytest.mark.django_db(transaction=True)
def test_a_run_in_one_worker_blocks_a_run_in_another(target, monkeypatch):
    started, release = threading.Event(), threading.Event()

    def run_suite(session_id, target_url, **kwargs):
        started.set()
        assert release.wait(10)
        return {"session_id": session_id, "results": [], "coverage": {}}, None

    monkeypatch.setattr(runner, "run_suite", run_suite)
    headers = {"Authorization": f"Bearer {TOKEN}"}
    client = Client(headers=headers)
    first = _setup(client).json()["session_id"]
    second = _setup(client).json()["session_id"]
    thread, result = _in_thread(lambda: _run(Client(headers=headers), first))
    try:
        assert started.wait(10)
        _assert_interface_error(_run(client, second), 409, "tester")
        _assert_interface_error(_setup(client), 409, "tester")
        _assert_interface_error(_report(client, first), 409, "tester")
    finally:
        release.set()
        thread.join(10)
    assert result["value"].status_code == 200
    assert _run(client, second).status_code == 200  # the slot is free again


@pytest.mark.django_db(transaction=True)
def test_two_runs_racing_start_only_one(target, monkeypatch):
    """Both workers check for a live run at the same moment. The check is slowed down so
    that, without the table lock, both would see none and both would start."""
    check = sessions._alive

    def slow_check():
        time.sleep(0.3)
        return check()

    monkeypatch.setattr(sessions, "_alive", slow_check)
    release = threading.Event()

    def run_suite(session_id, target_url, **kwargs):
        assert release.wait(10)
        return {"session_id": session_id, "results": [], "coverage": {}}, None

    monkeypatch.setattr(runner, "run_suite", run_suite)
    headers = {"Authorization": f"Bearer {TOKEN}"}
    ids = [_setup(Client(headers=headers)).json()["session_id"] for _ in range(2)]
    barrier = threading.Barrier(2)

    def race(session_id):
        def work():
            barrier.wait(5)
            return _run(Client(headers=headers), session_id)

        return work

    threads = [_in_thread(race(session_id)) for session_id in ids]
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if any("value" in result for _, result in threads):
            break
        time.sleep(0.05)
    release.set()
    for thread, _ in threads:
        thread.join(10)
    statuses = sorted(result["value"].status_code for _, result in threads)
    assert statuses == [200, 409]
    loser = next(result["value"] for _, result in threads if result["value"].status_code == 409)
    assert loser.json() == {**loser.json(), "message": ANOTHER_RUN, "source": "tester"}


@pytest.mark.django_db
def test_claim_answers_for_each_case():
    _running("run-live", heartbeat_age=5)
    Session.objects.create(session_id="ready", target_url=TARGET, created_at=Now())
    Session.objects.create(session_id="done", target_url=TARGET, created_at=Now(), state="finished")
    assert sessions.claim("nope") == sessions.UNKNOWN
    assert sessions.claim("done") == sessions.USED
    assert sessions.claim("run-live") == sessions.USED
    assert sessions.claim("ready") == sessions.BUSY
    Session.objects.filter(pk="run-live").update(state="finished")
    assert sessions.claim("ready") == sessions.CLAIMED
    assert Session.objects.get(pk="ready").state == "running"


# --- recovering a run cut off by a restart -------------------------------------------

PROGRESS = {
    PLANNED[0]: {"test": PLANNED[0], "outcome": "passed", "message": ""},
    PLANNED[1]: {"test": PLANNED[1], "outcome": "failed", "message": "expected 409, got 200"},
}


@pytest.mark.django_db
def test_a_run_without_a_heartbeat_is_reported_as_cut_off(authed, target, suite, no_target):
    stale = sessions.HEARTBEAT_STALE + 5
    _running("run-cut", heartbeat_age=stale, planned=PLANNED, progress=PROGRESS)
    stored = _report(authed, "run-cut")
    described.assert_described(described.TESTER, "/test/report", "get", stored, 200)
    results = stored.json()["results"]
    assert [r["test_id"] for r in results] == PLANNED
    assert [r["outcome"] for r in results] == ["pass", "fail", "error", "skip"]
    assert results[1]["message"] == "expected 409, got 200"
    assert results[2]["source"] == "tester"
    assert results[2]["message"] == f"Not evaluated: {sessions.CUT_OFF}."
    assert stored.json()["coverage"]["code"]["covered"] is None
    assert _report(authed, "run-cut").json() == stored.json()  # unchanged from now on
    again = _run(authed, "run-cut")
    _assert_interface_error(again, 409, "tester")
    assert again.json()["message"] == "This session has already run"
    assert target == []  # recovery doesn't touch the target


@pytest.mark.django_db
def test_a_run_past_its_time_limit_is_cut_off_despite_a_heartbeat(authed, no_target):
    _running("run-old", heartbeat_age=5, run_age=sessions.RUN_STALE + 5, planned=PLANNED)
    stored = _report(authed, "run-old")
    assert stored.status_code == 200
    assert [r["outcome"] for r in stored.json()["results"]] == ["error", "skip", "skip", "skip"]


@pytest.mark.django_db
def test_a_session_left_running_before_heartbeats_existed_is_recovered(authed, no_target):
    _running("run-legacy", heartbeat_age=None)
    Session.objects.filter(pk="run-legacy").update(started_at=None)
    stored = _report(authed, "run-legacy")
    described.assert_described(described.TESTER, "/test/report", "get", stored, 200)
    assert [r["test_id"] for r in stored.json()["results"]] == PLANNED
    assert stored.json()["results"][0]["source"] == "tester"


@pytest.mark.django_db
def test_a_cut_off_run_no_longer_blocks_setup_or_runs(authed, target, suite, no_target):
    _running("run-cut", heartbeat_age=sessions.HEARTBEAT_STALE + 5, planned=PLANNED)
    session_id = _setup(authed).json()["session_id"]
    assert Session.objects.get(pk="run-cut").state == "finished"
    assert _run(authed, session_id).status_code == 200


@pytest.mark.django_db
def test_a_live_run_is_not_taken_for_cut_off(authed, no_target):
    _running("run-live", heartbeat_age=sessions.HEARTBEAT_STALE - 30, run_age=1500)
    sessions.recover_stale()
    assert Session.objects.get(pk="run-live").state == "running"


@pytest.mark.django_db
def test_a_run_taken_for_cut_off_keeps_the_stored_report(authed, target, no_target, monkeypatch):
    """If the run was recovered while it was still going (no heartbeat got through for
    minutes), its late report doesn't replace the stored one, and it doesn't clean up a
    target that the next run may already be using."""

    def run_suite(session_id, target_url, **kwargs):
        Session.objects.filter(pk=session_id).update(heartbeat_at=None)
        sessions.recover_stale()  # another request finds it stale
        return {"session_id": session_id, "results": [], "coverage": {}}, None

    monkeypatch.setattr(runner, "run_suite", run_suite)
    session_id = _setup(authed).json()["session_id"]
    response = _run(authed, session_id)
    _assert_interface_error(response, 500, "tester")
    assert response.json()["message"] == sessions.CUT_OFF
    stored = _report(authed, session_id).json()
    assert [r["outcome"] for r in stored["results"]] == ["error", "skip", "skip", "skip"]
    assert _calls(target)[1:] == []


# --- the heartbeat ----------------------------------------------------------------------


@pytest.mark.django_db
def test_a_run_saves_its_planned_tests(authed, target, no_target, monkeypatch):
    lines = "".join(f'{{"test": "{t}", "outcome": "passed"}}\n' for t in PLANNED)
    monkeypatch.setattr(runner, "_pytest", base._fake_pytest(lines, 0))
    session_id = _setup(authed).json()["session_id"]
    assert _run(authed, session_id).status_code == 200
    assert Session.objects.get(pk=session_id).planned == PLANNED


@pytest.mark.django_db
def test_a_beat_refreshes_the_heartbeat_and_saves_progress(tmp_path):
    _running("run-1", heartbeat_age=100)
    before = Session.objects.get(pk="run-1").heartbeat_at
    progress = tmp_path / "progress.jsonl"
    progress.write_text(
        json.dumps({"test": PLANNED[0], "outcome": "passed"})
        + "\n"
        + json.dumps({"test": PLANNED[1], "outcome": "failed", "message": "x" * 900})
        + "\n",
        encoding="utf-8",
    )
    heartbeat = sessions.Heartbeat("run-1")
    heartbeat.started(PLANNED, tmp_path / "report.json", progress)
    heartbeat.beat()
    session = Session.objects.get(pk="run-1")
    assert session.heartbeat_at > before
    assert session.planned == PLANNED
    assert session.progress[PLANNED[0]]["outcome"] == "passed"
    assert len(session.progress[PLANNED[1]]["message"]) == runner.MESSAGE_LIMIT


@pytest.mark.django_db(transaction=True)
def test_the_heartbeat_thread_beats_until_stopped(monkeypatch):
    monkeypatch.setattr(sessions, "HEARTBEAT_INTERVAL", 0.05)
    _running("run-1", heartbeat_age=100)
    before = Session.objects.get(pk="run-1").heartbeat_at
    heartbeat = sessions.Heartbeat("run-1")
    heartbeat.start()
    try:
        deadline = time.monotonic() + 5
        while Session.objects.get(pk="run-1").heartbeat_at == before:
            assert time.monotonic() < deadline
            time.sleep(0.05)
    finally:
        heartbeat.stop()
    assert not heartbeat._thread.is_alive()
