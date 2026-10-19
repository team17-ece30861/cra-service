from django.db import models


class TesterSession(models.Model):
    """One tester session (the course's cross-team testing interface): created by
    POST /tester/test/setup, run once, and its report kept for lookup."""

    session_id = models.CharField(max_length=200, primary_key=True)
    target_url = models.CharField(max_length=2000)
    state = models.CharField(max_length=10, default="ready")  # ready, running, finished
    report = models.JSONField(null=True)
    created_at = models.DateTimeField()
