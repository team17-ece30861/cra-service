"""Runs Team 17's acceptance suite (acceptance/) against a target system for the
course's cross-team testing interface, and builds the suite report.

The suite runs in a pytest subprocess with only the target's token in its
environment, so it never sees this service's database or secrets.
"""

import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

from django.conf import settings

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE_INI = ROOT / "acceptance" / "pytest.ini"

# Seconds. The request limits registered for the tester must cover these.
SETUP_TIMEOUT = 60
SUITE_TIMEOUT = 480
REPORT_TIMEOUT = 30

# Our own client name in settings.API_TOKENS, used when the tester targets this service.
SELF_CLIENT = "team17"

ACCEPTANCE_CRITERIA_TOTAL = 19  # AC-01 to AC-19 in docs/spec.md
COMMUNICATION_FAILURE = re.compile(
    r"URLError|timed out|TimeoutError|Connection(Refused|Reset)Error|RemoteDisconnected"
)
MESSAGE_LIMIT = 500


class CommunicationError(Exception):
    pass


def allowed_target(target_url: str) -> bool:
    """Only this service and the approved pod systems, so the tester can't be used to
    send requests (or our tokens) anywhere else."""
    host = (urlsplit(target_url).hostname or "").lower()
    return host in settings.ALLOWED_HOSTS or host in settings.TESTER_ALLOWED_HOSTS


def target_token(target_url: str) -> str | None:
    host = urlsplit(target_url).netloc.lower()
    tokens = settings.TESTER_TARGET_TOKENS
    for key in (target_url.rstrip("/").lower(), host):
        if key in tokens:
            return tokens[key]
    if host.split(":")[0] in settings.ALLOWED_HOSTS:
        return settings.API_TOKENS.get(SELF_CLIENT)
    return None


def call(target_url: str, method: str, path: str, body=None, *, timeout: int):
    """One JSON request to the target. Returns (status, body as a dict, or {})."""
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token := target_token(target_url):
        headers["Authorization"] = f"Bearer {token}"
    request = Request(target_url + path, data=data, method=method, headers=headers)
    try:
        response = urlopen(request, timeout=timeout)
    except HTTPError as error:
        response = error
    except (URLError, OSError) as error:
        raise CommunicationError(f"{method} {path} failed: {type(error).__name__}") from None
    with response:
        try:
            parsed = json.loads(response.read().decode("utf-8") or "{}")
        except (ValueError, OSError):
            parsed = {}
    return response.code, parsed if isinstance(parsed, dict) else {}


def _pytest(*args: str, env: dict | None = None, timeout: int) -> subprocess.CompletedProcess:
    # The test path goes before the suite's own options (--base-url and so on), so
    # pytest loads acceptance/conftest.py, which defines them, before parsing them.
    command = [sys.executable, "-m", "pytest", str(ROOT / "acceptance"), "-c", str(ACCEPTANCE_INI)]
    return subprocess.run(
        [*command, "-p", "no:cacheprovider", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def planned_tests() -> list[str]:
    done = _pytest("--collect-only", "-q", env=_child_env(), timeout=60)
    return [line.strip() for line in done.stdout.splitlines() if "::" in line]


def _child_env(token: str | None = None) -> dict:
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1"}
    if token is not None:
        env["CRA_API_TOKEN"] = token
    return env


def _result(test_id: str, entry: dict | None) -> dict:
    if entry is None or entry["outcome"] == "not_run":
        return {"test_id": test_id, "outcome": "skip", "message": "Not executed."}
    if entry["outcome"] == "passed":
        return {"test_id": test_id, "outcome": "pass", "message": "Passed."}
    if entry["outcome"] == "skipped":
        return {"test_id": test_id, "outcome": "skip", "message": "Skipped by the suite."}
    message = (entry.get("message") or "Failed.")[:MESSAGE_LIMIT]
    if COMMUNICATION_FAILURE.search(message):
        return {
            "test_id": test_id,
            "outcome": "error",
            "source": "communication",
            "message": message,
        }
    return {"test_id": test_id, "outcome": "fail", "message": message}


def _code_coverage(target_url: str, session_id: str) -> dict:
    unavailable = "Target code coverage was unavailable"
    try:
        status, body = call(
            target_url,
            "GET",
            "/test/report?session_id=" + quote(session_id, safe=""),
            timeout=REPORT_TIMEOUT,
        )
    except CommunicationError:
        return {
            "covered": None,
            "total": None,
            "basis": f"{unavailable}: no response from /test/report",
        }
    code = body.get("coverage", {}).get("code") if status == 200 else None
    if isinstance(code, dict) and code.get("basis") and {"covered", "total"} <= code.keys():
        return {"covered": code["covered"], "total": code["total"], "basis": code["basis"]}
    return {
        "covered": None,
        "total": None,
        "basis": f"{unavailable}: /test/report returned {status}",
    }


def _system_coverage(results: list[dict]) -> dict:
    executed = [r["test_id"] for r in results if r["outcome"] != "skip"]
    criteria = {match for test_id in executed for match in re.findall(r"test_ac(\d\d)", test_id)}
    return {
        "covered": len(criteria),
        "total": ACCEPTANCE_CRITERIA_TOTAL,
        "basis": "Pod acceptance criteria AC-01 to AC-19 with at least one executed test, "
        "identified by test name",
    }


def run_suite(session_id: str, target_url: str) -> tuple[dict, str | None]:
    """Run the whole suite once. Returns the report and, if the tester aborted, why."""
    planned = planned_tests()
    entries: dict[str, dict] = {}
    aborted = None
    with tempfile.TemporaryDirectory() as tmp:
        report_path = Path(tmp) / "report.json"
        token = target_token(target_url) or "no-token-configured"
        try:
            done = _pytest(
                "-q",
                "--base-url",
                target_url,
                "--allow-reset",
                "--report",
                str(report_path),
                env=_child_env(token),
                timeout=SUITE_TIMEOUT,
            )
            if done.returncode not in (0, 1):
                aborted = f"The test suite stopped with exit code {done.returncode}"
        except subprocess.TimeoutExpired:
            aborted = f"The test suite did not finish within {SUITE_TIMEOUT} seconds"
        if report_path.exists():
            for entry in json.loads(report_path.read_text(encoding="utf-8"))["results"]:
                entries[entry["test"]] = entry
    if aborted:
        logger.error("Tester session %s aborted: %s", session_id, aborted)
    results = [_result(test_id, entries.get(test_id)) for test_id in planned]
    if aborted:
        results = [
            {**r, "message": f"Not executed: {aborted}."} if r["outcome"] == "skip" else r
            for r in results
        ]
    report = {
        "session_id": session_id,
        "target_url": target_url,
        "results": results,
        "coverage": {
            "code": _code_coverage(target_url, session_id),
            "component": {
                "covered": None,
                "total": None,
                "basis": "The pod specification does not define a component list yet",
            },
            "system": _system_coverage(results),
        },
    }
    return report, aborted
