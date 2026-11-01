import uuid

from django.db import models


class FixedClock(models.Model):
    """The fixed test time, if any (REQ-16)."""
    at = models.DateTimeField()


class TesterSession(models.Model):
    """A session for the course's cross-team tester."""

    session_id = models.CharField(max_length=200, primary_key=True)
    target_url = models.CharField(max_length=2000)
    state = models.CharField(max_length=10, default="ready")
    report = models.JSONField(null=True)


class SystemSession(models.Model):
    """A session prepared by POST /test/setup."""

    session_id = models.CharField(max_length=200, primary_key=True)
    created_at = models.DateTimeField()


class Ticket(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    state = models.CharField(max_length=20, default="received")
    resolution = models.CharField(max_length=30, null=True)
    received_at = models.DateTimeField()
    aware_at = models.DateTimeField(null=True)
    data = models.JSONField()


class ReportSubmission(models.Model):
    """Locked snapshot of a submitted report for one ticket/report type."""

    REPORT_TYPES = [
        ("early_warning", "early_warning"),
        ("notification", "notification"),
        ("final_report", "final_report"),
    ]

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    submitted_at = models.DateTimeField()
    reference = models.CharField(max_length=200, null=True, blank=True)
    content = models.JSONField()
    actor = models.CharField(max_length=200)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["ticket", "report_type"],
                name="unique_ticket_submission_per_report_type",
            )
        ]


class AuditEntry(models.Model):
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="audit_entries",
    )
    seq = models.PositiveIntegerField()
    at = models.DateTimeField()
    actor = models.CharField(max_length=200)
    action = models.CharField(max_length=30)
    changes = models.JSONField()
    reason = models.TextField(null=True)

    class Meta:
        ordering = ["seq"]
        constraints = [
            models.UniqueConstraint(
                fields=["ticket", "seq"],
                name="unique_ticket_audit_seq",
            )
        ]
