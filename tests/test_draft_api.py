"""Local live/locked draft integration; stored rows are fixtures, not submission API proof."""

import json
from copy import deepcopy
from datetime import timedelta

import pytest

from acceptance.client import Service
from acceptance.draft_cases import (
    CONTENT,
    DUE,
    FIELDS,
    FIXED,
    REPORTER,
    DraftChecks,
    create_reportable,
    read_draft,
)
from core.models import AuditEntry, ReportSubmission, Ticket
from cra_service.timestamps import parse_timestamp
from tests.test_phase3_api import DjangoTransport

REPORT_TYPES = ("early_warning", "notification", "final_report")


@pytest.fixture
def service():
    return Service(DjangoTransport())


def store_snapshot(ticket_id, report_type, *, submitted_at=None):
    return ReportSubmission.objects.create(
        ticket_id=ticket_id,
        report_type=report_type,
        submitted_at=submitted_at or parse_timestamp(FIXED),
        reference="receipt-17",
        content={"ticket_id": ticket_id, "aware_at": FIXED, **deepcopy(CONTENT[report_type])},
        actor="external-recorder",
    )


@pytest.mark.django_db(transaction=True)
class TestLocalDrafts(DraftChecks):
    pass


@pytest.mark.django_db(transaction=True)
class TestStoredDrafts:
    @pytest.fixture(autouse=True)
    def fresh_service(self, service):
        service.expect("POST", "/test/reset", 204, actor=None)
        service.fix_clock(FIXED)

    @pytest.mark.parametrize("report_type", REPORT_TYPES)
    @pytest.mark.parametrize(
        "seconds,status", [(-1, "submitted"), (0, "submitted"), (1, "submitted_late")]
    )
    def test_locked_report_status_uses_submission_time_not_current_clock(
        self, service, report_type, seconds, status
    ):
        ticket_id = create_reportable(service, **deepcopy(FIELDS))
        submission_time = parse_timestamp(DUE[report_type]) + timedelta(seconds=seconds)
        submission = store_snapshot(ticket_id, report_type, submitted_at=submission_time)
        service.fix_clock("2026-10-20T09:00:00Z")
        first = read_draft(service, ticket_id, report_type)
        service.fix_clock(FIXED)
        second = read_draft(service, ticket_id, report_type)
        assert first == second
        assert second["status"] == status
        assert second["due_at"] == DUE[report_type]
        assert second["content"] == submission.content
        assert second["submitted_at"] == submission_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        assert second["reference"] == "receipt-17"
        assert second["missing_fields"] == []
        assert ReportSubmission.objects.count() == 1
        assert AuditEntry.objects.count() == 2

    @pytest.mark.parametrize("report_type", REPORT_TYPES)
    def test_locked_content_ignores_later_ticket_edits_and_missing_live_fields(
        self, service, report_type
    ):
        ticket_id = create_reportable(service, **deepcopy(FIELDS))
        submission = store_snapshot(ticket_id, report_type)
        original = deepcopy(submission.content)
        service.expect(
            "PATCH",
            f"/tickets/{ticket_id}",
            200,
            template="/tickets/{id}",
            body={
                "product": {"name": "Changed", "affected_versions": []},
                "member_states": None,
                "vulnerability": None,
                "fix": None,
                "aware_at": "2026-10-04T09:00:00Z",
                "change_reason": "Earlier evidence",
            },
        )
        draft = read_draft(service, ticket_id, report_type)
        assert draft["content"] == original
        assert draft["missing_fields"] == []
        assert draft["content"]["aware_at"] == FIXED
        assert REPORTER not in json.dumps(draft)
        submission.refresh_from_db()
        assert submission.content == original
        assert submission.actor == "external-recorder"
        advisory = read_draft(service, ticket_id, "user_advisory")
        assert advisory["content"]["product"]["name"] == "Changed"
        assert "product.affected_versions" in advisory["missing_fields"]

    def test_current_deadline_can_change_status_without_changing_stored_content(self, service):
        ticket_id = create_reportable(service, **deepcopy(FIELDS))
        submission = store_snapshot(
            ticket_id, "early_warning", submitted_at=parse_timestamp("2026-10-06T09:00:00Z")
        )
        assert read_draft(service, ticket_id, "early_warning")["status"] == "submitted"
        service.expect(
            "PATCH",
            f"/tickets/{ticket_id}",
            200,
            template="/tickets/{id}",
            body={"aware_at": "2026-10-04T09:00:00Z", "change_reason": "Earlier evidence"},
        )
        draft = read_draft(service, ticket_id, "early_warning")
        assert draft["due_at"] == "2026-10-05T09:00:00Z"
        assert draft["status"] == "submitted_late"
        assert draft["content"] == submission.content

    @pytest.mark.parametrize("report_type", [*REPORT_TYPES, "user_advisory"])
    def test_resolved_tickets_keep_all_four_reports_readable_without_writes(
        self, service, report_type
    ):
        ticket_id = create_reportable(service, **deepcopy(FIELDS))
        stored = {report: store_snapshot(ticket_id, report) for report in REPORT_TYPES}
        Ticket.objects.filter(pk=ticket_id).update(state="closed", resolution="resolved")
        before = service.get(ticket_id)
        audit = list(AuditEntry.objects.values())
        draft = read_draft(service, ticket_id, report_type)
        expected_content = {"ticket_id": ticket_id, "aware_at": FIXED, **CONTENT[report_type]}
        assert draft["content"] == expected_content
        if report_type in REPORT_TYPES:
            assert draft["content"] == stored[report_type].content
            assert draft["status"] == "submitted"
        else:
            assert draft["status"] is draft["submitted_at"] is draft["reference"] is None
        assert service.get(ticket_id) == before
        assert list(AuditEntry.objects.values()) == audit
        assert ReportSubmission.objects.count() == 3

    def test_global_auth_and_size_precedence_still_apply_to_draft_paths(self, service):
        path = "/tickets/not-an-id/reports/unknown"
        body = b"x" * 65537
        unauthorized = service.transport.send("GET", path, raw=body, authenticated=False)
        assert unauthorized.status == 401
        too_large = service.transport.send("GET", path, raw=body)
        assert too_large.status == 413
        assert json.loads(too_large.body)["status"] == 413
        assert too_large.content_type == "application/problem+json"
        assert (
            Ticket.objects.count()
            == ReportSubmission.objects.count()
            == AuditEntry.objects.count()
            == 0
        )
