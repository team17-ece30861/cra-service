"""The recorded-report table (4.A1): one locked snapshot per ticket and report type."""

from datetime import UTC, datetime

import pytest
from django.db import IntegrityError, transaction

from core.models import ReportSubmission, Ticket

pytestmark = pytest.mark.django_db

AT = datetime(2026, 10, 6, 9, tzinfo=UTC)


def _ticket():
    return Ticket.objects.create(received_at=AT, data={"title": "t"})


def _record(ticket, report_type="early_warning", **fields):
    return ReportSubmission.objects.create(
        ticket=ticket,
        report_type=report_type,
        submitted_at=fields.pop("submitted_at", AT),
        content=fields.pop("content", {"title": "t"}),
        actor=fields.pop("actor", "analyst"),
        **fields,
    )


def test_a_ticket_can_record_each_report_type_once():
    ticket = _ticket()
    for report_type in ("early_warning", "notification", "final_report"):
        _record(ticket, report_type)

    assert ticket.submissions.count() == 3


def test_recording_the_same_report_type_twice_is_rejected():
    ticket = _ticket()
    _record(ticket)

    with pytest.raises(IntegrityError), transaction.atomic():
        _record(ticket)
    assert ticket.submissions.count() == 1


def test_two_tickets_can_each_record_the_same_report_type():
    _record(_ticket())
    _record(_ticket())

    assert ReportSubmission.objects.count() == 2


def test_reference_is_optional_and_content_is_stored_as_given():
    content = {"title": "t", "member_states": ["DE", "NL"], "fix": None}
    submission = _record(_ticket(), content=content)
    submission.refresh_from_db()

    assert submission.reference is None
    assert submission.content == content


def test_deleting_a_ticket_deletes_its_recorded_reports():
    ticket = _ticket()
    _record(ticket)
    ticket.delete()

    assert not ReportSubmission.objects.exists()


# transaction=True commits the row first. Inside one transaction, Postgres refuses to
# TRUNCATE a table with pending foreign-key checks; a real reset is its own request.
@pytest.mark.django_db(transaction=True)
def test_reset_clears_recorded_reports(authed):
    _record(_ticket())

    assert authed.post("/test/reset").status_code == 204
    assert not ReportSubmission.objects.exists()
