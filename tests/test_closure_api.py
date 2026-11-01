"""Local closure persistence, failure rollback, and genuine PostgreSQL concurrency."""

import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Barrier

import pytest
from django.db import connection, connections
from django.test import Client

from acceptance.client import Service
from acceptance.closure_cases import (
    ClosureChecks,
    close_ticket,
    closure_state,
    ready_to_close,
)
from acceptance.draft_cases import FIELDS, FIXED, REPORTER, create_reportable
from acceptance.submission_cases import REPORT_TYPES, audit_log, submit_report
from core import tickets
from core.models import AuditEntry, ReportSubmission, Ticket
from cra_service.timestamps import parse_timestamp
from tests.conftest import TOKEN
from tests.problems import assert_problem
from tests.test_phase3_api import DjangoTransport


@pytest.fixture
def service():
    return Service(DjangoTransport())


@pytest.mark.django_db(transaction=True)
class TestLocalClosures(ClosureChecks):
    pass


@pytest.mark.django_db(transaction=True)
class TestClosurePersistence:
    @pytest.fixture(autouse=True)
    def fresh_service(self, service):
        service.expect("POST", "/test/reset", 204, actor=None)
        service.fix_clock(FIXED)

    def test_close_updates_only_state_resolution_and_one_safe_audit(self, service):
        ticket_id = ready_to_close(service)
        before = Ticket.objects.values().get(pk=ticket_id)
        reports = list(ReportSubmission.objects.values().order_by("pk"))
        close_ticket(service, ticket_id, actor=" closer ")
        assert Ticket.objects.values().get(pk=ticket_id) == {
            **before,
            "state": "closed",
            "resolution": "resolved",
        }
        assert list(ReportSubmission.objects.values().order_by("pk")) == reports
        entry = AuditEntry.objects.get(ticket_id=ticket_id, action="closed")
        assert entry.actor == "closer"
        assert entry.at == parse_timestamp(FIXED)
        assert entry.reason is None
        assert entry.changes == [
            {"field": "resolution", "old": None, "new": "resolved"},
            {"field": "state", "old": "reportable", "new": "closed"},
        ]
        assert REPORTER not in json.dumps(entry.changes)

    @pytest.mark.parametrize("failure_point", ["audit", "render"])
    def test_failure_after_state_save_rolls_back_every_change_and_retry_has_no_gap(
        self, service, monkeypatch, caplog, failure_point
    ):
        ticket_id = ready_to_close(service)
        before = closure_state(service, ticket_id)
        stored = Ticket.objects.values().get(pk=ticket_id)
        reports = list(ReportSubmission.objects.values().order_by("pk"))
        original_audit = tickets._audit
        secret = "private-closure-failure-detail"

        def fail_audit(*args, **kwargs):
            original_audit(*args, **kwargs)
            raise RuntimeError(secret)

        def fail_render(*args, **kwargs):
            raise RuntimeError(secret)

        client = Client(headers={"Authorization": f"Bearer {TOKEN}", "X-Actor": "rollback"})
        with monkeypatch.context() as context:
            context.setattr(
                tickets,
                "_audit" if failure_point == "audit" else "_render",
                fail_audit if failure_point == "audit" else fail_render,
            )
            response = client.post(f"/tickets/{ticket_id}/close")
        problem = assert_problem(response, 500, "Internal server error")
        assert secret not in json.dumps(problem)
        assert secret not in caplog.text
        assert REPORTER not in caplog.text
        assert closure_state(service, ticket_id) == before
        assert Ticket.objects.values().get(pk=ticket_id) == stored
        assert list(ReportSubmission.objects.values().order_by("pk")) == reports
        close_ticket(service, ticket_id)
        assert [entry["seq"] for entry in audit_log(service, ticket_id)] == list(range(1, 7))

    def test_close_reads_clock_once_for_audit_and_rendering(self, service, monkeypatch):
        ticket_id = ready_to_close(service)
        calls = []

        def fixed_now():
            calls.append(True)
            return parse_timestamp(FIXED)

        with monkeypatch.context() as context:
            context.setattr(tickets.clock, "now", fixed_now)
            closed = close_ticket(service, ticket_id)
        assert len(calls) == 1
        assert closed["state"] == "closed"
        assert audit_log(service, ticket_id)[-1]["at"] == FIXED

    @pytest.mark.parametrize("missing_report", REPORT_TYPES)
    def test_actual_stored_set_not_row_count_controls_closure(self, service, missing_report):
        ticket_id = ready_to_close(service)
        ReportSubmission.objects.filter(ticket_id=ticket_id, report_type=missing_report).delete()
        before = closure_state(service, ticket_id)
        close_ticket(service, ticket_id, 409)
        assert closure_state(service, ticket_id) == before

    @pytest.mark.parametrize("now", [FIXED, "2026-11-01T09:00:00Z"])
    def test_bodyless_route_cannot_accept_client_state_changes(self, service, now):
        ticket_id = ready_to_close(service)
        before = Ticket.objects.values().get(pk=ticket_id)
        close_ticket(
            service,
            ticket_id,
            body={"state": "received", "resolution": "invalid", "aware_at": now},
        )
        assert Ticket.objects.values().get(pk=ticket_id) == {
            **before,
            "state": "closed",
            "resolution": "resolved",
        }

    def test_postgresql_concurrent_closes_have_one_success_and_one_audit(self, service):
        if connection.vendor != "postgresql":
            pytest.skip("Row-lock behavior requires PostgreSQL; not established by SQLite tests")
        ticket_id = ready_to_close(service)
        gate = Barrier(2)

        def attempt(number):
            actor = f"closer-{number}"
            try:
                gate.wait(timeout=10)
                response = DjangoTransport().send(
                    "POST", f"/tickets/{ticket_id}/close", actor=actor
                )
                return response.status, actor
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, range(2)))
        assert sorted(status for status, actor in results) == [200, 409]
        assert AuditEntry.objects.filter(ticket_id=ticket_id, action="closed").count() == 1
        assert ReportSubmission.objects.filter(ticket_id=ticket_id).count() == 3
        winner = next(actor for status, actor in results if status == 200)
        assert audit_log(service, ticket_id)[-1]["actor"] == winner
        assert Ticket.objects.get(pk=ticket_id).state == "closed"

    def test_postgresql_final_recording_and_close_serialize_on_the_same_ticket(self, service):
        if connection.vendor != "postgresql":
            pytest.skip("Row-lock behavior requires PostgreSQL; not established by SQLite tests")
        ticket_id = create_reportable(service, **deepcopy(FIELDS))
        for report_type in REPORT_TYPES[:2]:
            submit_report(service, ticket_id, report_type)
        gate = Barrier(2)

        def attempt(operation):
            suffix = "/close" if operation == "close" else "/reports/final_report/submission"
            try:
                gate.wait(timeout=10)
                response = DjangoTransport().send(
                    "POST", f"/tickets/{ticket_id}{suffix}", actor=operation
                )
                return operation, response.status
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = dict(pool.map(attempt, ["close", "record"]))
        assert results["record"] == 200
        assert results["close"] in (200, 409)
        if results["close"] == 409:
            assert Ticket.objects.get(pk=ticket_id).state == "reportable"
            assert not AuditEntry.objects.filter(ticket_id=ticket_id, action="closed").exists()
            close_ticket(service, ticket_id)
        assert Ticket.objects.get(pk=ticket_id).state == "closed"
        assert ReportSubmission.objects.filter(ticket_id=ticket_id).count() == 3
        assert [entry["seq"] for entry in audit_log(service, ticket_id)] == list(range(1, 7))
