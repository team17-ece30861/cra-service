import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import connection, connections
from django.test import Client

from acceptance.cases import Phase3Checks
from acceptance.client import Response, Service
from core.models import AuditEntry, Ticket
from tests.conftest import TOKEN


class DjangoTransport:
    def send(
        self,
        method,
        path,
        *,
        body=None,
        raw=None,
        actor="phase3-tests",
        authenticated=True,
        token=None,
    ):
        headers = {}
        if actor is not None:
            headers["X-Actor"] = actor
        if authenticated:
            headers["Authorization"] = "Bearer " + (token if token is not None else TOKEN)
        data = json.dumps(body).encode("utf-8") if body is not None else raw or b""
        response = Client().generic(
            method, path, data, content_type="application/json", headers=headers
        )
        return Response(response.status_code, response.get("Content-Type", ""), response.content)


@pytest.fixture
def service():
    return Service(DjangoTransport())


# PostgreSQL reset needs committed requests, matching deployed HTTP transactions.
@pytest.mark.django_db(transaction=True)
class TestLocalPhase3(Phase3Checks):
    def test_audit_has_one_entry_per_success_and_no_reporter(self, service):
        ticket = service.create()
        body = {
            "decision": "actively_exploited",
            "aware_at": "2026-10-05T09:00:00Z",
            "reason": "Confirmed",
        }
        service.triage(ticket["id"], body)
        service.triage(ticket["id"], body, 409)
        audit = service.expect(
            "GET", "/tickets/" + ticket["id"] + "/audit", 200, template="/tickets/{id}/audit"
        )
        assert [entry["seq"] for entry in audit] == [1, 2]
        assert [entry["action"] for entry in audit] == ["created", "triaged"]
        assert all(entry["actor"] == "phase3-tests" for entry in audit)
        assert "reporter@example.invalid" not in json.dumps(audit)
        assert "Simulated Reporter" not in json.dumps(audit)

    def test_unknown_ticket_precedes_invalid_body_and_missing_actor(self, service):
        service.expect(
            "POST",
            "/tickets/not-an-id/triage",
            404,
            template="/tickets/{id}/triage",
            raw=b"{bad",
            actor=None,
        )

    def test_failed_update_preserves_data_and_audit(self, service):
        ticket = service.create()
        service.triage(
            ticket["id"],
            {
                "decision": "actively_exploited",
                "aware_at": "2026-10-05T09:00:00Z",
                "reason": "Confirmed",
            },
        )
        before = service.get(ticket["id"])
        service.expect(
            "PATCH",
            "/tickets/" + ticket["id"],
            422,
            template="/tickets/{id}",
            body={
                "title": "Must not persist",
                "aware_at": "2026-10-05T09:00:01Z",
                "change_reason": "Test",
            },
        )
        assert service.get(ticket["id"]) == before
        assert AuditEntry.objects.count() == 2

    def test_update_merges_nested_fields_and_recalculates(self, service):
        ticket = service.create(member_states=["DE"])
        service.triage(
            ticket["id"],
            {
                "decision": "actively_exploited",
                "aware_at": "2026-10-05T09:00:00Z",
                "reason": "Confirmed",
            },
        )
        result = service.expect(
            "PATCH",
            "/tickets/" + ticket["id"],
            200,
            template="/tickets/{id}",
            body={
                "product": {"name": "Updated Router"},
                "member_states": ["NL"],
                "aware_at": "2026-10-04T09:00:00Z",
                "change_reason": "Earlier evidence",
            },
        )
        assert result["product"] == {
            "manufacturer": "Acme",
            "name": "Updated Router",
            "affected_versions": ["4.1.0"],
        }
        assert result["member_states"] == ["NL"]
        assert result["obligations"]["early_warning"]["due_at"] == "2026-10-05T09:00:00Z"
        assert AuditEntry.objects.count() == 3

    def test_reset_removes_application_rows_but_keeps_clock(self, service):
        service.create()
        service.expect("POST", "/test/reset", 204, actor=None)
        assert Ticket.objects.count() == AuditEntry.objects.count() == 0
        assert service.expect("GET", "/test/clock", 200, actor=None) == {
            "now": "2026-10-05T09:00:00Z"
        }

    def _patch(self, service, id, body, status):
        return service.expect(
            "PATCH", "/tickets/" + id, status, template="/tickets/{id}", body=body
        )

    def test_unrelated_update_ignores_stored_future_fix_time(self, service):
        # POST /tickets has no fix-time rule in the contract, so a future fix can be stored.
        ticket = service.create(fix={"available_at": "2030-01-01T00:00:00Z"})
        result = self._patch(service, ticket["id"], {"title": "Renamed"}, 200)
        assert result["title"] == "Renamed"
        result = self._patch(service, ticket["id"], {"fix": {"description": "Patch"}}, 200)
        assert result["fix"]["available_at"] == "2030-01-01T00:00:00Z"
        assert AuditEntry.objects.count() == 3

    def test_unrelated_update_after_clock_moves_back(self, service):
        ticket = service.create(fix={"available_at": "2026-10-05T09:00:00Z"})
        service.fix_clock("2026-10-01T00:00:00Z")
        assert self._patch(service, ticket["id"], {"title": "Renamed"}, 200)["title"] == "Renamed"

    def test_sent_future_fix_time_is_rejected_without_changes(self, service):
        ticket = service.create()
        before = service.get(ticket["id"])
        problem = self._patch(
            service,
            ticket["id"],
            {"title": "Must not persist", "fix": {"available_at": "2026-10-05T09:00:01Z"}},
            422,
        )
        assert [error["field"] for error in problem["errors"]] == ["fix.available_at"]
        assert service.get(ticket["id"]) == before
        assert AuditEntry.objects.count() == 1

    def test_clearing_fix_skips_the_fix_time_check(self, service):
        ticket = service.create(fix={"available_at": "2030-01-01T00:00:00Z"})
        assert self._patch(service, ticket["id"], {"fix": None}, 200)["fix"] is None

    def test_awareness_change_needs_reason_and_reportable_state(self, service):
        # AC-07: no reason is 422; a received ticket is 409.
        ticket = service.create()
        self._patch(service, ticket["id"], {"aware_at": "2026-10-05T08:00:00Z"}, 409)
        service.triage(
            ticket["id"],
            {"decision": "actively_exploited", "aware_at": "2026-10-05T09:00:00Z", "reason": "x"},
        )
        problem = self._patch(service, ticket["id"], {"aware_at": "2026-10-05T08:00:00Z"}, 422)
        assert [error["field"] for error in problem["errors"]] == ["change_reason"]
        assert AuditEntry.objects.count() == 2

    def test_out_of_range_deadline_is_rejected_without_partial_write(self, service):
        service.fix_clock("9999-12-31T23:59:59Z")
        ticket = service.create()
        before = service.get(ticket["id"])
        service.triage(
            ticket["id"],
            {
                "decision": "actively_exploited",
                "aware_at": "9999-12-31T23:59:59Z",
                "reason": "Boundary input",
            },
            422,
        )
        assert service.get(ticket["id"]) == before
        assert AuditEntry.objects.count() == 1

    def test_out_of_range_fix_deadline_names_the_fix_field(self, service):
        service.fix_clock("9999-12-31T23:59:59Z")
        ticket = service.create(fix={"available_at": "9999-12-31T23:59:59Z"})
        before = service.get(ticket["id"])
        problem = service.triage(
            ticket["id"],
            {
                "decision": "actively_exploited",
                "aware_at": "2026-10-05T09:00:00Z",
                "reason": "Boundary input",
            },
            422,
        )
        assert problem["errors"][0]["field"] == "fix.available_at"
        assert service.get(ticket["id"]) == before
        assert AuditEntry.objects.count() == 1

    @pytest.mark.django_db(transaction=True)
    def test_concurrent_triage_has_one_success_and_one_audit_entry(self, service):
        if connection.vendor != "postgresql":
            pytest.skip("Row-lock behavior requires PostgreSQL; exercised in Linux CI")
        ticket = service.create()
        gate = Barrier(2)
        body = {
            "decision": "actively_exploited",
            "aware_at": "2026-10-05T09:00:00Z",
            "reason": "Confirmed",
        }

        def attempt():
            try:
                gate.wait(timeout=10)
                return (
                    DjangoTransport()
                    .send("POST", "/tickets/" + ticket["id"] + "/triage", body=body)
                    .status
                )
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: attempt(), range(2)))
        assert sorted(results) == [200, 409]
        assert AuditEntry.objects.count() == 2
