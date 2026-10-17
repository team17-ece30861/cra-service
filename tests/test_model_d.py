"""AC-03 deadline and status oracles copied from Phase 2 Model D E1-E5."""

import json
from pathlib import Path

import pytest

from core.domain.deadlines import calculate_deadlines
from core.domain.statuses import unsubmitted_obligation_status
from cra_service.timestamps import parse_timestamp

FIXTURE = Path(__file__).parent / "fixtures" / "phase3_model_d.json"
CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_model_d_exact_published_deadlines(case):
    fix = case.get("fix_available_at")
    deadlines = calculate_deadlines(
        parse_timestamp(case["aware_at"]), parse_timestamp(fix) if fix is not None else None
    )
    actual = {
        "early_warning": deadlines.early_warning_due,
        "notification": deadlines.notification_due,
        "final_report": deadlines.final_report_due,
    }

    for report_type, expected in case["expected_deadlines"].items():
        assert actual[report_type] == parse_timestamp(expected)


@pytest.mark.parametrize(
    "case", [case for case in CASES if "expected_statuses" in case], ids=lambda case: case["id"]
)
def test_model_d_exact_published_statuses(case):
    deadlines = calculate_deadlines(parse_timestamp(case["aware_at"]))
    due_times = {
        "early_warning": deadlines.early_warning_due,
        "notification": deadlines.notification_due,
        "final_report": deadlines.final_report_due,
    }

    for report_type, expected in case["expected_statuses"].items():
        assert (
            unsubmitted_obligation_status(
                report_type=report_type,
                applicable=True,
                due_at=due_times[report_type],
                now=parse_timestamp(case["now"]),
            )
            == expected
        )
