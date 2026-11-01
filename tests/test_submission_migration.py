"""Upgrade the current main schema without recreating its ticket/audit/session tables."""

from datetime import UTC, datetime

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_submission_migration_preserves_existing_core_data():
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    previous = [("core", "0003_systemsession")]
    try:
        executor.migrate(previous)
        old_apps = executor.loader.project_state(previous).apps
        now = datetime(2026, 10, 5, 9, tzinfo=UTC)
        ticket = old_apps.get_model("core", "Ticket").objects.create(
            state="reportable", received_at=now, aware_at=now, data={"title": "Existing ticket"}
        )
        old_apps.get_model("core", "AuditEntry").objects.create(
            ticket_id=ticket.pk, seq=1, at=now, actor="existing-actor", action="created", changes=[]
        )
        old_apps.get_model("core", "SystemSession").objects.create(
            session_id="existing-session", created_at=now
        )
        old_apps.get_model("core", "FixedClock").objects.create(pk=1, at=now)

        executor = MigrationExecutor(connection)
        executor.migrate(latest)
        new_apps = executor.loader.project_state(latest).apps
        assert new_apps.get_model("core", "Ticket").objects.get(pk=ticket.pk).data == {
            "title": "Existing ticket"
        }
        assert new_apps.get_model("core", "AuditEntry").objects.get(ticket_id=ticket.pk).seq == 1
        assert (
            new_apps.get_model("core", "SystemSession")
            .objects.filter(pk="existing-session")
            .exists()
        )
        assert new_apps.get_model("core", "FixedClock").objects.get(pk=1).at == now
        submissions = new_apps.get_model("core", "ReportSubmission")
        assert submissions.objects.count() == 0
        submissions.objects.create(
            ticket_id=ticket.pk,
            report_type="early_warning",
            submitted_at=now,
            reference=None,
            content={"ticket_id": str(ticket.pk)},
            actor="new-actor",
        )
        assert submissions.objects.get().ticket_id == ticket.pk
    finally:
        MigrationExecutor(connection).migrate(latest)
