"""Database-free closure cases for every combination of submitted reports."""

from dataclasses import FrozenInstanceError
from itertools import combinations

import pytest

from core.domain.closure import ClosureResult, close_ticket
from cra_service.errors import Conflict

REPORTS = ("early_warning", "notification", "final_report")
SUBMITTED_SETS = [subset for size in range(4) for subset in combinations(REPORTS, size)]


@pytest.mark.parametrize("submitted_reports", SUBMITTED_SETS)
def test_only_all_three_reports_permit_reportable_ticket_closure(submitted_reports):
    if set(submitted_reports) == set(REPORTS):
        assert close_ticket(
            state="reportable", submitted_reports=submitted_reports
        ) == ClosureResult(state="closed", resolution="resolved")
    else:
        with pytest.raises(Conflict) as excinfo:
            close_ticket(state="reportable", submitted_reports=submitted_reports)
        assert excinfo.value.status == 409


@pytest.mark.parametrize("state", ["received", "closed"])
@pytest.mark.parametrize("submitted_reports", SUBMITTED_SETS)
def test_non_reportable_tickets_cannot_be_resolved_even_with_all_reports(state, submitted_reports):
    with pytest.raises(Conflict) as excinfo:
        close_ticket(state=state, submitted_reports=submitted_reports)
    assert excinfo.value.status == 409


@pytest.mark.parametrize("missing_report", REPORTS)
def test_advisory_does_not_replace_a_required_report(missing_report):
    submitted_reports = [report for report in REPORTS if report != missing_report] + [
        "user_advisory"
    ]
    with pytest.raises(Conflict):
        close_ticket(state="reportable", submitted_reports=submitted_reports)


@pytest.mark.parametrize("submitted_reports", [list(REPORTS), ["early_warning"]])
def test_closure_does_not_mutate_stored_report_types(submitted_reports):
    before = submitted_reports.copy()
    if len(submitted_reports) == 3:
        close_ticket(state="reportable", submitted_reports=submitted_reports)
    else:
        with pytest.raises(Conflict):
            close_ticket(state="reportable", submitted_reports=submitted_reports)
    assert submitted_reports == before


def test_closure_result_is_immutable():
    result = close_ticket(state="reportable", submitted_reports=REPORTS)
    with pytest.raises(FrozenInstanceError):
        result.state = "reportable"
