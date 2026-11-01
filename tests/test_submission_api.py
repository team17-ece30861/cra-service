"""Local transaction/storage checks; PostgreSQL concurrency is not simulated as passing."""

import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Barrier

import pytest
from django.db import IntegrityError, connection, connections
from django.db.models import QuerySet
from django.test import Client

from acceptance.client import Service
from acceptance.draft_cases import FIELDS, FIXED, REPORTER, create_reportable
from acceptance.submission_cases import (
    REPORT_TYPES,
    SubmissionChecks,
    audit_log,
    observable_state,
    record_previous,
    submit_report,
)
from core import tickets
from core.models import AuditEntry, ReportSubmission, Ticket
from cra_service.errors import RuleViolation, field_error
from cra_service.timestamps import parse_timestamp
from tests.conftest import TOKEN
from tests.problems import assert_problem
from tests.test_phase3_api import DjangoTransport


@pytest.fixture
def service():
    return Service(DjangoTransport())


@pytest.mark.django_db(transaction=True)
class TestLocalSubmissions(SubmissionChecks):
    pass


@pytest.mark.django_db(transaction=True)
class TestSubmissionPersistence:
    @pytest.fixture(autouse=True)
    def fresh_service(self, service):
        service.expect("POST", "/test/reset", 204, actor=None)
        service.fix_clock(FIXED)

    @pytest.mark.parametrize("report_type", REPORT_TYPES)
    def test_actual_row_and_audit_capture_the_same_validated_snapshot(self, service, report_type):
        ticket_id = create_reportable(service, **deepcopy(FIELDS))
        record_previous(service, ticket_id, report_type)
        recorded = submit_report(
            service,
            ticket_id,
            report_type,
            body={"reference": "external-receipt"},
            actor=" recorder ",
        )
        stored = ReportSubmission.objects.get(ticket_id=ticket_id, report_type=report_type)
        assert stored.content == recorded["content"]
        assert stored.submitted_at == parse_timestamp(FIXED)
        assert stored.reference == "external-receipt"
        assert stored.actor == "recorder"
        entry = audit_log(service, ticket_id)[-1]
        assert entry["changes"] == [
            {
                "field": f"reports.{report_type}",
                "old": None,
                "new": {
                    "submitted_at": FIXED,
                    "reference": "external-receipt",
                    "content": recorded["content"],
                    "actor": "recorder",
                },
            }
        ]
        assert REPORTER not in json.dumps(entry)

    def test_audit_failure_after_both_inserts_rolls_back_every_write(
        self, service, monkeypatch, caplog
    ):
        ticket_id = create_reportable(service, **deepcopy(FIELDS))
        before = observable_state(service, ticket_id)
        original_audit = tickets._audit
        secret = "private-database-error-detail"

        def failing_audit(*args, **kwargs):
            original_audit(*args, **kwargs)
            raise RuntimeError(secret)

        client = Client(headers={"Authorization": f"Bearer {TOKEN}", "X-Actor": "rollback-test"})
        with monkeypatch.context() as context:
            context.setattr(tickets, "_audit", failing_audit)
            response = client.post(
                f"/tickets/{ticket_id}/reports/early_warning/submission",
                {},
                content_type="application/json",
            )
        problem = assert_problem(response, 500, "Internal server error")
        assert secret not in json.dumps(problem)
        assert secret not in caplog.text
        assert REPORTER not in caplog.text
        assert observable_state(service, ticket_id) == before
        assert ReportSubmission.objects.count() == 0
        submit_report(service, ticket_id)
        assert [entry["seq"] for entry in audit_log(service, ticket_id)] == [1, 2, 3]

    def test_render_rule_failure_after_recording_rolls_back_snapshot_and_audit(
        self, service, monkeypatch
    ):
        ticket_id = create_reportable(service, **deepcopy(FIELDS))
        before = observable_state(service, ticket_id)

        def failing_render(*args, **kwargs):
            raise RuleViolation([field_error("submitted_at", "injected response failure")])

        with monkeypatch.context() as context:
            context.setattr(tickets, "_render_draft", failing_render)
            submit_report(service, ticket_id, status=422)
        assert observable_state(service, ticket_id) == before
        assert ReportSubmission.objects.count() == 0

    def test_unique_constraint_fallback_returns_conflict_without_partial_writes(
        self, service, monkeypatch
    ):
        ticket_id = create_reportable(service, **deepcopy(FIELDS))
        before = observable_state(service, ticket_id)
        original_exists = QuerySet.exists

        def fail_insert(*args, **kwargs):
            raise IntegrityError("simulated unique constraint collision")

        def competing_row_exists(query):
            if query.model is ReportSubmission:
                return True
            return original_exists(query)

        with monkeypatch.context() as context:
            context.setattr(ReportSubmission.objects, "create", fail_insert)
            context.setattr(QuerySet, "exists", competing_row_exists)
            submit_report(service, ticket_id, status=409)
        assert observable_state(service, ticket_id) == before
        assert ReportSubmission.objects.count() == 0

    def test_unrelated_integrity_failure_is_not_misreported_as_duplicate(
        self, service, monkeypatch
    ):
        ticket_id = create_reportable(service, **deepcopy(FIELDS))
        before = observable_state(service, ticket_id)

        def fail_insert(*args, **kwargs):
            raise IntegrityError("simulated unrelated database failure")

        client = Client(headers={"Authorization": f"Bearer {TOKEN}", "X-Actor": "rollback-test"})
        with monkeypatch.context() as context:
            context.setattr(ReportSubmission.objects, "create", fail_insert)
            response = client.post(
                f"/tickets/{ticket_id}/reports/early_warning/submission",
                {},
                content_type="application/json",
            )
        assert_problem(response, 500, "Internal server error")
        assert observable_state(service, ticket_id) == before
        assert ReportSubmission.objects.count() == 0

    def test_recording_uses_one_clock_value_for_submission_audit_and_response(
        self, service, monkeypatch
    ):
        ticket_id = create_reportable(service, **deepcopy(FIELDS))
        calls = []

        def fixed_now():
            calls.append(True)
            return parse_timestamp(FIXED)

        with monkeypatch.context() as context:
            context.setattr(tickets.clock, "now", fixed_now)
            recorded = submit_report(service, ticket_id)
        assert len(calls) == 1
        assert recorded["submitted_at"] == audit_log(service, ticket_id)[-1]["at"] == FIXED

    @pytest.mark.parametrize("report_type", REPORT_TYPES)
    def test_resolved_ticket_rejects_all_recording(self, service, report_type):
        ticket_id = create_reportable(service, **deepcopy(FIELDS))
        for report in REPORT_TYPES:
            submit_report(service, ticket_id, report)
        Ticket.objects.filter(pk=ticket_id).update(state="closed", resolution="resolved")
        before = observable_state(service, ticket_id)
        submit_report(service, ticket_id, report_type, 409)
        assert observable_state(service, ticket_id) == before
        assert ReportSubmission.objects.count() == 3

    def test_postgresql_concurrent_duplicate_has_one_success_and_one_audit(self, service):
        if connection.vendor != "postgresql":
            pytest.skip("Row-lock behavior requires PostgreSQL; not established by SQLite tests")
        ticket_id = create_reportable(service, **deepcopy(FIELDS))
        gate = Barrier(2)

        def attempt(number):
            actor = f"concurrent-{number}"
            try:
                gate.wait(timeout=10)
                response = DjangoTransport().send(
                    "POST",
                    f"/tickets/{ticket_id}/reports/early_warning/submission",
                    body={},
                    actor=actor,
                )
                return response.status, actor
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, range(2)))
        assert sorted(status for status, actor in results) == [200, 409]
        assert ReportSubmission.objects.count() == 1
        assert AuditEntry.objects.count() == 3
        winner = next(actor for status, actor in results if status == 200)
        assert ReportSubmission.objects.get().actor == winner
        assert audit_log(service, ticket_id)[-1]["actor"] == winner
