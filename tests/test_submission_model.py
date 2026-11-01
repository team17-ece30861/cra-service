"""Supplemental persistence/reset checks for Ann's model merged in PR #76."""

from datetime import UTC, datetime

import pytest
from django.db import IntegrityError, transaction

from core import clock
from core.models import FixedClock, ReportSubmission, SystemSession, Ticket

NOW = datetime(2026, 10, 5, 9, tzinfo=UTC)
REPORT_TYPES = ("early_warning", "notification", "final_report")
pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def ticket():
    return Ticket.objects.create(state="reportable", received_at=NOW, aware_at=NOW, data={})


def record(ticket, report_type="early_warning", **overrides):
    values = {
        "submitted_at": NOW,
        "reference": "receipt-17",
        "content": {"ticket_id": str(ticket.pk), "product": {"name": "Router"}},
        "actor": "submission-review",
        **overrides,
    }
    return ReportSubmission.objects.create(ticket=ticket, report_type=report_type, **values)


@pytest.mark.parametrize("report_type", REPORT_TYPES)
def test_submission_fields_and_ticket_relation_survive_a_database_read(ticket, report_type):
    submission = record(ticket, report_type)
    stored = ticket.submissions.get(pk=submission.pk)
    assert stored.report_type == report_type
    assert stored.submitted_at == NOW
    assert stored.reference == "receipt-17"
    assert stored.actor == "submission-review"
    assert stored.content == {"ticket_id": str(ticket.pk), "product": {"name": "Router"}}


@pytest.mark.parametrize("report_type", REPORT_TYPES)
def test_database_rejects_duplicate_report_type_for_a_ticket(ticket, report_type):
    record(ticket, report_type)
    with pytest.raises(IntegrityError), transaction.atomic():
        record(ticket, report_type)
    assert ticket.submissions.count() == 1


def test_each_ticket_can_record_all_three_types_and_other_tickets_independently(ticket):
    other = Ticket.objects.create(received_at=NOW, data={})
    for report_type in REPORT_TYPES:
        record(ticket, report_type)
        record(other, report_type)
    assert ticket.submissions.count() == other.submissions.count() == 3


def test_null_reference_matches_the_published_interface(ticket):
    submission = record(ticket, reference=None)
    submission.refresh_from_db()
    assert submission.reference is None


def test_stored_snapshot_does_not_follow_later_changes_to_source_values(ticket):
    content = {"product": {"name": "Original"}, "member_states": ["DE"]}
    submission = record(ticket, content=content)
    content["product"]["name"] = "Changed"
    content["member_states"].append("FR")
    submission.refresh_from_db()
    assert submission.content == {"product": {"name": "Original"}, "member_states": ["DE"]}


def test_deleting_a_ticket_cascades_to_its_submission_rows(ticket):
    record(ticket)
    ticket.delete()
    assert not ReportSubmission.objects.exists()


def test_reset_clears_submissions_but_preserves_clock_and_system_sessions(ticket, authed):
    record(ticket)
    clock.fix(NOW)
    SystemSession.objects.create(session_id="review-session", created_at=NOW)
    assert authed.post("/test/reset").status_code == 204
    assert not ReportSubmission.objects.exists()
    assert not Ticket.objects.exists()
    assert FixedClock.objects.get(pk=1).at == NOW
    assert SystemSession.objects.filter(pk="review-session").exists()
