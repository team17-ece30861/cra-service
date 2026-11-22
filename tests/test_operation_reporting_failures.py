"""Exercise real pytest lifecycles that previously hid incomplete runs or setup failures."""

import json
import os
import subprocess
import sys

import pytest

from acceptance.client import ROOT


@pytest.mark.parametrize(
    "mode",
    [
        "service-fixture-failure",
        "dependent-fixture-failure",
        "setup-assertion-failure",
        "early-stop",
        "early-exit-zero",
        "filtered",
        "file-selection",
        "node-selection",
        "directory-selection",
        "ignored-file",
        "ignored-glob",
        "collection-error",
    ],
)
def test_report_retains_setup_failures_and_identifies_incomplete_runs(tmp_path, mode):
    (tmp_path / "pytest.ini").write_text("[pytest]\naddopts = -p no:django\n", encoding="utf-8")
    fixture = (
        "import pytest\n"
        "from acceptance.client import Response, Service\n"
        "class FakeTransport:\n"
        "    def send(self, method, path, **kwargs):\n"
    )
    if mode == "service-fixture-failure":
        fixture += '        return Response(500, "application/problem+json", b"{}")\n'
    else:
        fixture += (
            '        if path == "/test/reset":\n'
            '            return Response(204, "", b"")\n'
            '        if path == "/test/clock":\n'
            f"            return Response({500 if mode == 'dependent-fixture-failure' else 200}, "
            '"application/json", b\'{"now":"2026-10-05T09:00:00Z"}\')\n'
            '        return Response(200, "application/json", b\'{"status":"ok"}\')\n'
        )
    fixture += (
        "@pytest.fixture\n"
        "def service():\n"
        "    instance = Service(FakeTransport())\n"
        '    instance.expect("POST", "/test/reset", 204)\n'
        "    return instance\n"
    )
    if mode in {"dependent-fixture-failure", "setup-assertion-failure"}:
        fixture += (
            "@pytest.fixture(autouse=True)\n"
            "def prepare(service):\n"
            '    service.expect("GET", "/test/clock", 200)\n'
        )
        if mode == "setup-assertion-failure":
            fixture += '    raise RuntimeError("synthetic preparation failure")\n'
    (tmp_path / "conftest.py").write_text(fixture, encoding="utf-8")
    test_source = (
        "import pytest\n"
        "def test_first(service):\n"
        '    service.expect("GET", "/health", 200)\n'
        "def test_second(service):\n"
        '    service.expect("GET", "/health", 200)\n'
        '    assert False, "synthetic semantic failure"\n'
        "def test_third(service):\n"
        '    service.expect("GET", "/health", 200)\n'
    )
    if mode == "early-exit-zero":
        test_source = test_source.replace(
            'assert False, "synthetic semantic failure"',
            'pytest.exit("synthetic early exit", returncode=0)',
        )
    (tmp_path / "test_cases.py").write_text(test_source, encoding="utf-8")
    target = str(tmp_path)
    if mode == "file-selection":
        target = str(tmp_path / "test_cases.py")
        (tmp_path / "test_omitted.py").write_text(
            "def test_omitted():\n    assert True\n", encoding="utf-8"
        )
    elif mode == "node-selection":
        target = str(tmp_path / "test_cases.py") + "::test_first"
    elif mode == "directory-selection":
        subset = tmp_path / "subset"
        subset.mkdir()
        (subset / "test_subset.py").write_text(
            "def test_subset():\n    assert True\n", encoding="utf-8"
        )
        target = str(subset)
    if mode == "collection-error":
        (tmp_path / "test_bad_collection.py").write_text("def invalid syntax\n", encoding="utf-8")
    environment = {
        key: os.environ[key]
        for key in ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP")
        if key in os.environ
    }
    environment.update({"PYTHONPATH": str(ROOT), "CRA_API_TOKEN": "synthetic-only"})
    extra = []
    if mode in {"ignored-file", "ignored-glob"}:
        ignored = tmp_path / "test_omitted.py"
        ignored.write_text("def test_omitted():\n    assert True\n", encoding="utf-8")
        extra = (
            ["--ignore", str(ignored)]
            if mode == "ignored-file"
            else ["--ignore-glob", "*omitted.py"]
        )
    if mode == "early-stop":
        extra = ["--maxfail=1"]
    elif mode == "filtered":
        extra = ["-k", "test_first"]
    elif mode == "collection-error":
        extra = ["--continue-on-collection-errors"]
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
            "acceptance.conftest",
            "-p",
            "no:cacheprovider",
            target,
            "--base-url=https://synthetic.example.invalid",
            "--allow-reset",
            "--report=" + str(tmp_path / "report.json"),
            "--operation-report=" + str(tmp_path / "operations.md"),
            "--progress=" + str(tmp_path / "progress.jsonl"),
            "-q",
            *extra,
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == (
        0 if mode in {"filtered", "early-exit-zero", "node-selection", "directory-selection"} else 1
    ), completed.stdout + completed.stderr
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    markdown = (tmp_path / "operations.md").read_text(encoding="utf-8")
    assert len(report["operations"]) == 14
    if "fixture-failure" in mode or mode == "setup-assertion-failure":
        assert report["failed"] == 3
        assert report["run_complete"] is True
        assert "Run: finished" in markdown
        assert all(entry["operation_checks"] for entry in report["results"])
        expected_checks = 1 if mode == "service-fixture-failure" else 2
        assert all(len(entry["operation_checks"]) == expected_checks for entry in report["results"])
        reset = next(row for row in report["operations"] if row["path"] == "/test/reset")
        assert reset["implementation"] != "success_observed"
        if mode == "service-fixture-failure":
            assert reset["success"]["failed_statuses"] == [204]
            assert all(
                entry["operation_checks"][0]["actual_status"] == 500 for entry in report["results"]
            )
        else:
            assert reset["success"]["inconclusive_statuses"] == [204]
            clock = next(
                row
                for row in report["operations"]
                if row["path"] == "/test/clock" and row["method"] == "GET"
            )
            expected = (
                "failed_statuses"
                if mode == "dependent-fixture-failure"
                else "inconclusive_statuses"
            )
            assert clock["success"][expected] == [200]
            assert clock["implementation"] != "success_observed"
    else:
        assert report["run_complete"] is False
        assert "Run: incomplete" in markdown
        assert "Run: finished" not in markdown
        if mode == "early-stop":
            assert report["tests_selected"] == 3
            assert report["tests_completed"] == 2
            assert report["tests_not_run"] == 1
        elif mode == "early-exit-zero":
            assert report["tests_selected"] == 3
            assert report["tests_completed"] == 1
            assert report["tests_not_run"] == 1
        elif mode == "filtered":
            assert report["tests_selected"] == report["tests_completed"] == 1
            assert report["tests_deselected"] == 2
        elif mode.endswith("selection"):
            assert report["partial_selection"] is True
            assert report["tests_deselected"] == 0
            assert (
                report["tests_selected"]
                == report["tests_completed"]
                == (3 if mode == "file-selection" else 1)
            )
        elif mode in {"ignored-file", "ignored-glob"}:
            assert report["collection_exclusions"] is True
            assert report["partial_selection"] is True
            assert report["tests_deselected"] == 0
            assert report["tests_selected"] == report["tests_completed"] == 3
        else:
            assert report["collection_errors"] == 1
        reset = next(row for row in report["operations"] if row["path"] == "/test/reset")
        assert reset["implementation"] == "not_demonstrated"
    progress = [
        json.loads(line)
        for line in (tmp_path / "progress.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert progress == [entry for entry in report["results"] if entry["teardown_complete"]]
    assert "synthetic-only" not in json.dumps(report["operations"])
