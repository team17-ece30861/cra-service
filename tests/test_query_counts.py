"""AC-18 (REQ-17): reads cost a fixed number of queries however many tickets are
stored, so their latency at 1,000 tickets comes from rendering, not the database."""

from datetime import UTC, datetime, timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from core.models import ReportSubmission, Ticket

NOW = datetime(2026, 10, 20, 12, 0, 0, tzinfo=UTC)
DATA = {
    "source": "customer",
    "title": "Authentication bypass",
    "description": "Simulated vulnerability.",
    "product": {"manufacturer": "Acme", "name": "Router OS", "affected_versions": ["4.1"]},
    "member_states": ["DE"],
    "reporter": {"name": "Simulated Reporter", "contact": "reporter@example.invalid"},
}
# The fixed clock, the tickets, and their recorded reports (one prefetch).
LIST_QUERIES = 3
# The fixed clock, the ticket, and its recorded reports.
DETAIL_QUERIES = 3


def store(count: int) -> list[Ticket]:
    """count tickets: a third received, a third reportable with an early warning
    recorded, a third closed as not reportable."""
    tickets = []
    for index in range(count):
        kind = index % 3
        tickets.append(
            Ticket(
                state=("received", "reportable", "closed")[kind],
                resolution="not_actively_exploited" if kind == 2 else None,
                received_at=NOW - timedelta(minutes=index),
                aware_at=NOW - timedelta(hours=index % 100 + 1) if kind == 1 else None,
                data=DATA,
            )
        )
    Ticket.objects.bulk_create(tickets)
    ReportSubmission.objects.bulk_create(
        ReportSubmission(
            ticket=ticket,
            report_type="early_warning",
            submitted_at=ticket.aware_at + timedelta(hours=1),
            content={},
            actor="perf",
        )
        for ticket in tickets
        if ticket.state == "reportable"
    )
    return tickets


def count_queries(client, path):
    with CaptureQueriesContext(connection) as queries:
        response = client.get(path)
    assert response.status_code == 200
    return len(queries), response.json()


@pytest.mark.django_db
@pytest.mark.parametrize("count", [3, 1000])
def test_list_query_count_does_not_grow_with_tickets(authed, count):
    store(count)
    queries, body = count_queries(authed, "/tickets")
    assert len(body) == count
    assert queries == LIST_QUERIES
    queries, body = count_queries(authed, "/tickets?obligation_status=submitted")
    assert len(body) == len([i for i in range(count) if i % 3 == 1])
    assert queries == LIST_QUERIES
    queries, _ = count_queries(authed, "/tickets?state=reportable")
    assert queries == LIST_QUERIES


@pytest.mark.django_db
@pytest.mark.parametrize("count", [3, 1000])
def test_detail_query_count_does_not_grow_with_tickets(authed, count):
    tickets = store(count)
    reportable = next(ticket for ticket in tickets if ticket.state == "reportable")
    queries, body = count_queries(authed, f"/tickets/{reportable.pk}")
    assert body["obligations"]["early_warning"]["status"] == "submitted"
    assert queries == DETAIL_QUERIES
