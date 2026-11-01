"""Database-free checks of the published submission rules and error precedence."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta, timezone
from itertools import combinations

import pytest

from core.domain.submissions import validate_submission
from cra_service.errors import Conflict, RuleViolation

AWARE = datetime(2026, 10, 2, 17, tzinfo=UTC)
NOW = datetime(2026, 10, 5, 9, tzinfo=UTC)
REPORTS = ("early_warning", "notification", "final_report")
SUBMITTED_SETS = [subset for size in range(4) for subset in combinations(REPORTS, size)]


def submit(**overrides):
    arguments = {
        "state": "reportable",
        "report_type": "early_warning",
        "aware_at": AWARE,
        "now": NOW,
        "submitted_reports": (),
        "missing_fields": (),
        **overrides,
    }
    return validate_submission(**arguments)


@pytest.mark.parametrize("report_type", REPORTS)
@pytest.mark.parametrize("submitted_reports", SUBMITTED_SETS)
def test_report_order_and_duplicates_for_every_stored_report_subset(report_type, submitted_reports):
    previous = {
        "early_warning": None,
        "notification": "early_warning",
        "final_report": "notification",
    }[report_type]
    allowed = report_type not in submitted_reports and (
        previous is None or previous in submitted_reports
    )
    if allowed:
        assert submit(report_type=report_type, submitted_reports=submitted_reports) == NOW
    else:
        with pytest.raises(Conflict) as excinfo:
            submit(report_type=report_type, submitted_reports=submitted_reports)
        assert excinfo.value.status == 409


@pytest.mark.parametrize("state", ["received", "closed"])
@pytest.mark.parametrize("report_type", REPORTS)
def test_a_ticket_with_no_awareness_is_rejected_by_state_not_by_time(state, report_type):
    # A received ticket, or one closed as not reportable, has aware_at None.
    with pytest.raises(Conflict) as excinfo:
        submit(state=state, report_type=report_type, aware_at=None)
    assert excinfo.value.status == 409


@pytest.mark.parametrize("state", ["received", "closed"])
@pytest.mark.parametrize("report_type", REPORTS)
def test_non_reportable_states_reject_each_report_before_rule_checks(state, report_type):
    with pytest.raises(Conflict) as excinfo:
        submit(
            state=state,
            report_type=report_type,
            missing_fields=["member_states"],
            submitted_at=NOW + timedelta(seconds=1),
        )
    assert excinfo.value.status == 409


@pytest.mark.parametrize(
    "report_type,submitted_reports",
    [
        ("early_warning", ["early_warning"]),
        ("notification", []),
        ("final_report", ["early_warning"]),
    ],
    ids=["duplicate", "missing-early-warning", "missing-notification"],
)
def test_submission_conflicts_precede_missing_fields_and_invalid_time(
    report_type, submitted_reports
):
    with pytest.raises(Conflict):
        submit(
            report_type=report_type,
            submitted_reports=submitted_reports,
            missing_fields=["member_states"],
            submitted_at=NOW + timedelta(seconds=1),
        )


@pytest.mark.parametrize("report_type", REPORTS)
def test_missing_fields_are_named_for_each_report(report_type):
    with pytest.raises(RuleViolation) as excinfo:
        submit(
            report_type=report_type,
            submitted_reports=list(REPORTS[: REPORTS.index(report_type)]),
            missing_fields=["product.affected_versions", "member_states"],
        )
    assert excinfo.value.status == 422
    assert excinfo.value.errors == [
        {"field": "product.affected_versions", "message": "required for this report"},
        {"field": "member_states", "message": "required for this report"},
    ]


@pytest.mark.parametrize("submitted_at", [AWARE, NOW, AWARE + timedelta(seconds=1)])
def test_submission_interval_includes_both_endpoints(submitted_at):
    assert submit(submitted_at=submitted_at) == submitted_at


def test_default_submission_time_is_supplied_now_even_after_deadline():
    assert submit() == NOW


def test_equal_awareness_and_now_permit_submission():
    assert submit(aware_at=NOW) == NOW


@pytest.mark.parametrize("submitted_at", [AWARE - timedelta(seconds=1), NOW + timedelta(seconds=1)])
def test_time_outside_interval_names_submitted_at(submitted_at):
    with pytest.raises(RuleViolation) as excinfo:
        submit(submitted_at=submitted_at)
    assert excinfo.value.status == 422
    assert excinfo.value.errors == [
        {"field": "submitted_at", "message": "must be between aware_at and now"}
    ]


def test_missing_fields_and_invalid_time_are_both_reported():
    with pytest.raises(RuleViolation) as excinfo:
        submit(missing_fields=["member_states"], submitted_at=NOW + timedelta(seconds=1))
    assert [error["field"] for error in excinfo.value.errors] == ["member_states", "submitted_at"]


@pytest.mark.parametrize("submitted_at", [None, AWARE, NOW])
def test_clock_moved_before_awareness_leaves_no_valid_interval(submitted_at):
    with pytest.raises(RuleViolation) as excinfo:
        submit(now=AWARE - timedelta(seconds=1), submitted_at=submitted_at)
    assert excinfo.value.errors[0]["field"] == "submitted_at"


@pytest.mark.parametrize("field", ["aware_at", "now", "submitted_at"])
def test_each_time_is_normalized_from_its_utc_offset(field):
    times = {"aware_at": AWARE, "now": NOW, "submitted_at": NOW}
    times[field] = times[field].astimezone(timezone(timedelta(hours=-5, minutes=-30)))
    result = submit(**times)
    assert result == NOW
    assert result.tzinfo is UTC


@pytest.mark.parametrize("submitted_at", [AWARE, NOW])
def test_fractional_seconds_are_truncated_before_boundary_checks(submitted_at):
    assert (
        submit(
            aware_at=AWARE.replace(microsecond=999_999),
            now=NOW.replace(microsecond=100_000),
            submitted_at=submitted_at.replace(microsecond=999_999),
        )
        == submitted_at
    )


def test_default_now_is_normalized_to_utc_seconds():
    local_now = NOW.astimezone(timezone(timedelta(hours=2))).replace(microsecond=123_456)
    result = submit(now=local_now)
    assert result == NOW
    assert result.tzinfo is UTC
    assert result.microsecond == 0


@pytest.mark.parametrize("field", ["aware_at", "now", "submitted_at"])
def test_naive_datetimes_are_internal_integration_errors(field):
    with pytest.raises(ValueError, match="timezone-aware"):
        submit(**{field: NOW.replace(tzinfo=None)})


@pytest.mark.parametrize("report_type", ["user_advisory", "unknown"])
def test_invalid_report_types_must_be_filtered_by_the_route(report_type):
    with pytest.raises(ValueError, match="unknown Article 14 report type"):
        submit(report_type=report_type)


@pytest.mark.parametrize("reject", [False, True])
def test_inputs_are_unchanged_after_success_or_rejection(reject):
    submitted_reports = ["early_warning"]
    missing_fields = ["member_states"] if reject else []
    before = deepcopy((submitted_reports, missing_fields))
    arguments = {
        "report_type": "notification",
        "submitted_reports": submitted_reports,
        "missing_fields": missing_fields,
    }
    if reject:
        with pytest.raises(RuleViolation):
            submit(**arguments)
    else:
        assert submit(**arguments) == NOW
    assert (submitted_reports, missing_fields) == before
