from django.db import models


class SignInFailure(models.Model):
    """One failed console sign-in (LIM-12). Kept in the database so both gunicorn workers
    and every instance count the same attempts. `username` is the normalized name tried
    (console.lockout.username_key), whether or not such an account exists. The failure
    that reaches the limit has `locks` set; the lock lasts from its `at`. Lives outside
    `core`, so POST /test/reset (which clears core's tables) leaves it alone."""

    username = models.CharField(max_length=150)
    at = models.DateTimeField()
    locks = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["username", "at"])]
