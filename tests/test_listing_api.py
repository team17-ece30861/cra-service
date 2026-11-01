"""AC-06 and AC-11 run locally through Django, plus checks only visible from inside."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from acceptance.client import Service
from acceptance.draft_cases import FIXED
from acceptance.listing_cases import ListingChecks, StatusChecks, reportable_at
from acceptance.submission_cases import submit_report
from tests.test_phase3_api import DjangoTransport


@pytest.fixture
def service():
    return Service(DjangoTransport())


@pytest.mark.django_db(transaction=True)
class TestLocalStatuses(StatusChecks):
    pass


@pytest.mark.django_db(transaction=True)
class TestLocalListing(ListingChecks):
    pass


@pytest.mark.django_db(transaction=True)
def test_list_reads_submissions_in_one_query_not_one_per_ticket(service):
    service.expect("POST", "/test/reset", 204, actor=None)
    service.fix_clock(FIXED)
    for _ in range(5):
        ticket_id = reportable_at(service, FIXED)
        submit_report(service, ticket_id, "early_warning")
    with CaptureQueriesContext(connection) as queries:
        tickets = service.expect("GET", "/tickets", 200)
    assert len(tickets) == 5
    assert all(t["obligations"]["early_warning"]["status"] == "submitted" for t in tickets)
    submission_queries = [q for q in queries if "core_reportsubmission" in q["sql"]]
    assert len(submission_queries) == 1
