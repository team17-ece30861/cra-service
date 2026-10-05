from django.db import models


class FixedClock(models.Model):
    """The fixed test time, if any (REQ-16). At most one row, with pk=1; while it
    exists, core.clock.now() returns `at` instead of real time. Stored in the
    database so every worker and instance sees the same clock."""

    at = models.DateTimeField()
