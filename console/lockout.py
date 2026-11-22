"""Limit failed console sign-ins (LIM-12, plan 5.8).

Five failures for one username within 15 minutes lock that username for 15 minutes from
the fifth. While it is locked every attempt fails with the same message, even with the
right password, and isn't counted (so the lock still ends 15 minutes after the fifth
failure). Usernames with no account are counted the same way, so the answer never says
whether an account exists. A successful sign-in clears the count. Only the console's
sign-in uses this; the API's bearer tokens are unaffected.

Timing uses real time (core.clock.real_now), never the pod's test clock: a clock left
fixed after a test run would otherwise make failures days apart add up to a lock that
never ends, and moving the test clock back would skip a lock.
"""

import logging
import math
import unicodedata
from datetime import datetime, timedelta

from django.db import connection

from console.models import SignInFailure

logger = logging.getLogger(__name__)

MAX_FAILURES = 5
WINDOW = timedelta(minutes=15)
LOCK = timedelta(minutes=15)
LOGGED_USERNAME_LENGTH = 64

# Postgres advisory lock namespace for sign-in attempts (any constant unique in this app).
_ADVISORY_NAMESPACE = 5812
_KEY_LENGTH = SignInFailure._meta.get_field("username").max_length


def username_key(raw: str) -> str:
    """The name attempts are counted under: trimmed, normalized the way Django's sign-in
    form normalizes usernames (NFKC), and case-folded. Empty when there is nothing to count."""
    value = (raw or "").replace("\x00", "").strip()[: _KEY_LENGTH * 2]
    return unicodedata.normalize("NFKC", value).casefold()[:_KEY_LENGTH]


def hold(key: str) -> None:
    """Serialize sign-ins for one username until the current transaction ends, so two
    workers can't both see four failures and let a sixth guess through."""
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_advisory_xact_lock(%s, hashtext(%s))", [_ADVISORY_NAMESPACE, key]
            )


def minutes_locked(key: str, now: datetime) -> int | None:
    """Whole minutes (rounded up) until the lock on `key` ends, or None if it isn't locked."""
    started = (
        SignInFailure.objects.filter(username=key, locks=True, at__gt=now - LOCK)
        .order_by("-at")
        .values_list("at", flat=True)
        .first()
    )
    if started is None:
        return None
    return _minutes(started + LOCK - now)


def record_failure(key: str, now: datetime, client_ip: str) -> int | None:
    """Count a failed attempt. Returns the lock's minutes if this failure starts a lock."""
    SignInFailure.objects.filter(at__lte=now - max(WINDOW, LOCK)).delete()
    failure = SignInFailure.objects.create(username=key, at=now)
    recent = SignInFailure.objects.filter(username=key, at__gt=now - WINDOW)
    if recent.count() < MAX_FAILURES:
        return None
    failure.locks = True
    failure.save(update_fields=["locks"])
    # Attacker-controlled values, so %r keeps them on one line. Never the password or body;
    # the username is cut short in case a password was typed into it.
    logger.warning(
        "Console sign-in locked for %d minutes after %d failures: username=%r client_ip=%r",
        LOCK // timedelta(minutes=1),
        MAX_FAILURES,
        key[:LOGGED_USERNAME_LENGTH],
        client_ip,
    )
    return _minutes(LOCK)


def clear(key: str) -> None:
    SignInFailure.objects.filter(username=key).delete()


def message(minutes: int) -> str:
    unit = "minute" if minutes == 1 else "minutes"
    return f"Too many attempts. Try again in {minutes} {unit}."


def client_ip(request) -> str:
    """The client's address for the log. On Cloud Run, Google's front end appends the
    address it saw to X-Forwarded-For, so the last entry is the one a client can't forge;
    REMOTE_ADDR is the proxy. Locally there is no header and REMOTE_ADDR is the client."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    last = forwarded.rsplit(",", 1)[-1].strip()
    return (last or request.META.get("REMOTE_ADDR", ""))[:64]


def _minutes(remaining: timedelta) -> int:
    return max(1, math.ceil(remaining.total_seconds() / 60))
