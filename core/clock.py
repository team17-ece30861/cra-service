"""The service's current time. Use clock.now(), never datetime.now() or timezone.now().

Returns the fixed test time when one is set (PUT /test/clock), otherwise real UTC
time. Either way the value is an aware UTC datetime truncated to the second.
clock.real_now() always returns real time; only security timing uses it.
"""

from datetime import datetime

from django.utils import timezone

from core.models import FixedClock
from cra_service.timestamps import to_utc_second

_PK = 1


def now() -> datetime:
    fixed = FixedClock.objects.filter(pk=_PK).values_list("at", flat=True).first()
    if fixed is not None:
        return to_utc_second(fixed)
    return _real_now()


def fix(at: datetime) -> datetime:
    """Fix the clock at `at` until it is changed or released. Returns the stored time."""
    at = to_utc_second(at)
    FixedClock.objects.update_or_create(pk=_PK, defaults={"at": at})
    return at


def release() -> None:
    """Return to real time."""
    FixedClock.objects.filter(pk=_PK).delete()


def real_now() -> datetime:
    """Real UTC time, truncated to the second, ignoring the fixed test clock. The sanctioned
    accessor for security timing that a test clock must not move, such as the console
    sign-in lockout (console/lockout.py). Everything else uses now()."""
    return _real_now()


def _real_now() -> datetime:
    # The one sanctioned call to the system clock.
    return to_utc_second(timezone.now())
