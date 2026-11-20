import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from acceptance.model_coverage import model_measure, read_model_journal, scenario_bindings

ROOT = Path(__file__).resolve().parents[1]
MAPPING = "https://example.invalid/design/team17-phase5-design-v1"
INTAKE_TEST = (
    "test_phase3.py::TestRemotePhase3::test_ac01_intake_has_unique_ids_and_fixed_receipt_time"
)


def environment():
    values = {
        key: os.environ[key]
        for key in ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP")
        if key in os.environ
    }
    values.update({"PYTHONPATH": str(ROOT), "CRA_API_TOKEN": "synthetic-only"})
    return values


@pytest.mark.parametrize(
    "mode,exit_code,covered",
    [
        ("passed", 0, 1),
        ("failed_oracle", 1, 1),
        ("skip_before", 0, 0),
        ("setup_failure", 1, 0),
        ("teardown_failure", 1, 1),
        ("interrupted_teardown", 2, 1),
    ],
)
def test_real_hooks_keep_only_oracles_reached_in_the_call(tmp_path, mode, exit_code, covered):
    fixture = (
        "import pytest\n"
        "from acceptance.model_coverage import model_scenario\n"
        "@pytest.fixture(autouse=True)\n"
        "def lifecycle():\n"
    )
    if mode == "setup_failure":
        fixture += (
            '    with model_scenario("A-01.intake"):\n'
            "        assert True\n"
            '    raise RuntimeError("synthetic setup failure")\n'
        )
    else:
        fixture += "    yield\n"
        if mode == "teardown_failure":
            fixture += '    raise RuntimeError("synthetic teardown failure")\n'
        elif mode == "interrupted_teardown":
            fixture += "    raise KeyboardInterrupt()\n"
    (tmp_path / "conftest.py").write_text(fixture, encoding="utf-8")
    test = (
        "import pytest\n"
        "from acceptance.model_coverage import model_scenario\n"
        "class TestRemotePhase3:\n"
        "    def test_ac01_intake_has_unique_ids_and_fixed_receipt_time(self):\n"
    )
    if mode == "skip_before":
        test += '        pytest.skip("synthetic skip before evaluation")\n'
    test += (
        '        with model_scenario("A-01.intake"):\n'
        f"            assert {mode != 'failed_oracle'}\n"
    )
    (tmp_path / "test_phase3.py").write_text(test, encoding="utf-8")
    journal = tmp_path / "model.jsonl"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-c",
            str(ROOT / "acceptance/pytest.ini"),
            "--rootdir",
            str(tmp_path),
            "-p",
            "no:cacheprovider",
            "-p",
            "acceptance.conftest",
            str(tmp_path / "test_phase3.py"),
            "--base-url=https://synthetic.example.invalid",
            "--allow-reset",
            "--model-progress=" + str(journal),
            "--report=" + str(tmp_path / "report.json"),
            "-q",
        ],
        cwd=tmp_path,
        env=environment(),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == exit_code, completed.stdout + completed.stderr
    recorded = read_model_journal(journal)
    measure = model_measure(recorded, [INTAKE_TEST], MAPPING)
    assert (measure["covered"], measure["total"]) == (covered, 44)
    assert all(set(event) == {"scenario", "satisfied"} for event in recorded["events"])
    assert "synthetic setup failure" not in json.dumps(recorded)
    if mode == "failed_oracle":
        assert recorded["events"] == [{"scenario": "A-01.intake", "satisfied": False}]


def test_actual_portable_cases_emit_bound_evidence_using_only_local_django(tmp_path):
    (tmp_path / "pytest.ini").write_text(
        "[pytest]\nDJANGO_SETTINGS_MODULE = cra_service.settings\n"
        "filterwarnings = ignore:No directory at:UserWarning\n",
        encoding="utf-8",
    )
    (tmp_path / "conftest.py").write_text(
        "import pytest\n"
        "from acceptance.client import Service\n"
        "from tests.test_phase3_api import DjangoTransport\n"
        'pytest_plugins = ["acceptance.conftest"]\n'
        "@pytest.fixture(autouse=True)\n"
        "def api_token_settings(settings):\n"
        '    settings.API_TOKENS = {"test": "test-token"}\n'
        "@pytest.fixture\n"
        "def service():\n"
        "    return Service(DjangoTransport())\n"
        "def pytest_collection_modifyitems(items):\n"
        "    for item in items:\n"
        "        item.add_marker(pytest.mark.django_db(transaction=True))\n",
        encoding="utf-8",
    )
    for source in (ROOT / "acceptance").glob("test_*.py"):
        (tmp_path / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    child_env = environment()
    child_env.update(
        {"DJANGO_SECRET_KEY": "local-model-only", "DATABASE_URL": "sqlite:///:memory:"}
    )
    report_path = tmp_path / "report.json"
    journal = tmp_path / "model.jsonl"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-c",
            str(tmp_path / "pytest.ini"),
            "--rootdir",
            str(tmp_path),
            "-p",
            "no:cacheprovider",
            str(tmp_path),
            "--base-url=http://127.0.0.1:9",
            "--allow-reset",
            "--report=" + str(report_path),
            "--model-progress=" + str(journal),
            "-q",
        ],
        cwd=tmp_path,
        env=child_env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    report = json.loads(report_path.read_text(encoding="utf-8"))
    planned = [result["test"] for result in report["results"]]
    assert report["tests_run"] == len(planned) == len(set(planned))
    assert (report["passed"], report["failed"], report["skipped"]) == (len(planned) - 1, 0, 1)
    assert [result["test"] for result in report["results"] if result["outcome"] == "skipped"] == [
        "test_phase3.py::test_ac15_plain_http_is_refused_or_redirected_to_https"
    ]
    expected = {binding for binding in scenario_bindings().values() if binding is not None}
    assert expected <= set(planned)
    recorded = read_model_journal(journal)
    assert recorded["available"] is True
    assert len({event["scenario"] for event in recorded["events"]}) == 140
    measure = model_measure(recorded, planned, MAPPING)
    assert (measure["covered"], measure["total"]) == (19, 44)
    assert all(
        result.get("model_evidence", {}).get("available", True) for result in report["results"]
    )
