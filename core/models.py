import uuid

from django.db import models


class FixedClock(models.Model):
    """The fixed test time, if any (REQ-16). At most one row, with pk=1; while it
    exists, core.clock.now() returns `at` instead of real time. Stored in the
    database so every worker and instance sees the same clock."""

    at = models.DateTimeField()


class SystemSession(models.Model):
    """A session prepared by POST /test/setup (the course's cross-team testing
    interface). Kept on reset, so a tester can still read GET /test/report after
    its suite resets the data."""

    session_id = models.CharField(max_length=200, primary_key=True)
    created_at = models.DateTimeField()


class Ticket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    state = models.CharField(max_length=20, default="received")
    resolution = models.CharField(max_length=30, null=True)
    received_at = models.DateTimeField()
    aware_at = models.DateTimeField(null=True)
    data = models.JSONField()


class AuditEntry(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="audit_entries")
    seq = models.PositiveIntegerField()
    at = models.DateTimeField()
    actor = models.CharField(max_length=200)
    action = models.CharField(max_length=30)
    changes = models.JSONField()
    reason = models.TextField(null=True)

    class Meta:
        ordering = ["seq"]
        constraints = [
            models.UniqueConstraint(fields=["ticket", "seq"], name="unique_ticket_audit_seq")
        ]
