from django.db import models


class TesterSession(models.Model):
    """One tester session (the course's cross-team testing interface): created by
    POST /tester/test/setup, run once, and its report kept for lookup.

    While a run is going, `heartbeat_at` is refreshed every half minute (database time,
    not core.clock: the suite fixes that clock when it targets this service), and
    `planned` and `progress` keep the planned tests and the outcomes recorded so far, so
    a run cut off by a restart can still be reported (tester.sessions)."""

    session_id = models.CharField(max_length=200, primary_key=True)
    target_url = models.CharField(max_length=2000)
    state = models.CharField(max_length=10, default="ready")  # ready, running, finished
    report = models.JSONField(null=True)
    created_at = models.DateTimeField()
    started_at = models.DateTimeField(null=True)
    heartbeat_at = models.DateTimeField(null=True)
    planned = models.JSONField(null=True)
    progress = models.JSONField(null=True)
