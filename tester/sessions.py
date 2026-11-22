"""Run rules for Team 17's deployed tester (docs/plan.md, task 5.8).

- One run at a time. Every client shares one database and one test clock, so while
  any session is running, a run for another session and a new setup get 409. The check
  and the claim happen under a table lock in one short transaction, so the service's
  two gunicorn workers can't both start a run.
- A run cut off by a restart or a crash is recovered. A running session's worker
  refreshes `heartbeat_at` every HEARTBEAT_INTERVAL seconds. A session with no heartbeat
  for HEARTBEAT_STALE seconds, or running longer than RUN_STALE, is treated as aborted:
  its recorded outcomes are kept, the test it was running is marked `error` (source
  `tester`), the rest `skip`, and the report is stored. This happens lazily, on the next
  setup, run or report request. Its session still can't run again.

Times come from the database (Now()), not core.clock: when the tester targets this
service, the suite fixes that clock in the same database.
"""

import logging
import threading
from datetime import timedelta

from django.db import connection, transaction
from django.db.models import Q
from django.db.models.functions import Now

from tester import runner
from tester.models import TesterSession

logger = logging.getLogger(__name__)

# Seconds.
HEARTBEAT_INTERVAL = 30
HEARTBEAT_STALE = 180
# Longer than the whole run can take (gunicorn stops a request at 1,800 s).
RUN_STALE = runner.SUITE_TIMEOUT + 300

CUT_OFF = "The tester's run was cut off before it finished (the service restarted or stopped)"

CLAIMED, UNKNOWN, USED, BUSY = "claimed", "unknown", "used", "busy"


def _alive() -> Q:
    return Q(
        state="running",
        heartbeat_at__gte=Now() - timedelta(seconds=HEARTBEAT_STALE),
        started_at__gte=Now() - timedelta(seconds=RUN_STALE),
    )


def _stale() -> Q:
    return Q(state="running") & (
        Q(heartbeat_at__isnull=True)
        | Q(heartbeat_at__lt=Now() - timedelta(seconds=HEARTBEAT_STALE))
        | Q(started_at__isnull=True)
        | Q(started_at__lt=Now() - timedelta(seconds=RUN_STALE))
    )


def _cut_off_report(session: TesterSession) -> dict:
    if session.planned is None:  # stopped before the suite started
        return runner.failed_report(session.session_id, session.target_url, CUT_OFF)
    return runner.cut_off_report(
        session.session_id, session.target_url, CUT_OFF, session.planned, session.progress or {}
    )


def recover_stale() -> None:
    """Finish every session whose run was cut off, storing its report. The target is
    not cleaned up here: by now another client may be using it."""
    for session in TesterSession.objects.filter(_stale()):
        report = _cut_off_report(session)
        # Only if it's still stale: a live run, or another request, may have got there.
        if TesterSession.objects.filter(_stale(), pk=session.pk).update(
            state="finished", report=report
        ):
            logger.error(
                "Tester session %s was cut off; stored its report without cleaning up the target",
                session.session_id,
            )


def run_in_progress() -> bool:
    recover_stale()
    return TesterSession.objects.filter(_alive()).exists()


def claim(session_id: str) -> str:
    """Start this session's run if it's ready and no other run is going. Returns
    CLAIMED, UNKNOWN (no such session), USED (already ran) or BUSY (another run)."""
    recover_stale()
    with transaction.atomic():
        with connection.cursor() as cursor:
            # Writers wait here one at a time; plain reads (report lookups) don't.
            cursor.execute(f"LOCK TABLE {TesterSession._meta.db_table} IN EXCLUSIVE MODE")
        state = TesterSession.objects.filter(pk=session_id).values_list("state", flat=True)
        if not state:
            return UNKNOWN
        if state[0] != "ready":
            return USED
        if TesterSession.objects.filter(_alive()).exists():
            return BUSY
        TesterSession.objects.filter(pk=session_id).update(
            state="running", started_at=Now(), heartbeat_at=Now()
        )
    return CLAIMED


def fresh_connection() -> None:
    """Drop this thread's database connection before using it again after a long run:
    a pooler or network may have closed it during the suite's 28 minutes, and Django
    only replaces a broken connection between requests. The tester's routes run outside
    a transaction (cra_service.middleware); inside one (a test's), it is left alone."""
    if not connection.in_atomic_block:
        connection.close()


def still_running(session_id: str) -> bool:
    return TesterSession.objects.filter(pk=session_id, state="running").exists()


def finish(session_id: str, report: dict) -> bool:
    """Store the report, unless recovery already stored one (the run was taken for cut
    off). Returns whether this report was stored."""
    return bool(
        TesterSession.objects.filter(pk=session_id, state="running").update(
            state="finished", report=report
        )
    )


def _trimmed(entries: dict[str, dict]) -> dict[str, dict]:
    return {
        test_id: {
            "test": test_id,
            "outcome": entry.get("outcome"),
            "message": (entry.get("message") or "")[: runner.MESSAGE_LIMIT],
        }
        for test_id, entry in entries.items()
    }


class Heartbeat:
    """Keeps a running session's heartbeat fresh from a background thread while its
    suite runs, and saves the planned tests and recorded outcomes for recovery."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.cancelled = False  # the session was taken for cut off: the run was stopped
        self._owner = threading.get_ident()  # the request thread running the suite
        self._paths = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="tester-heartbeat", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=10)

    def started(self, planned, report_path, progress_path) -> None:
        """runner.run_suite's on_start: the suite is about to start."""
        self._paths = (report_path, progress_path)
        TesterSession.objects.filter(pk=self.session_id, state="running").update(
            planned=planned, heartbeat_at=Now()
        )

    def beat(self) -> None:
        fields = {"heartbeat_at": Now()}
        if self._paths is not None:
            entries = runner._recorded_entries(*self._paths)
            if entries:
                fields["progress"] = _trimmed(entries)
        if not TesterSession.objects.filter(pk=self.session_id, state="running").update(**fields):
            # Recovery already took this run for cut off and stored its report, and the
            # slot may belong to another run now: stop the suite, and the run finishes
            # without storing anything or cleaning up (tester.api.run).
            logger.error(
                "Tester session %s was taken for cut off while running; stopping it",
                self.session_id,
            )
            self.cancelled = True
            self._stop.set()
            runner.stop_child(self._owner)

    def _loop(self) -> None:
        while not self._stop.wait(HEARTBEAT_INTERVAL):
            try:
                self.beat()
            except Exception as error:
                logger.warning(
                    "Tester session %s: heartbeat failed: %s",
                    self.session_id,
                    type(error).__name__,
                )
            finally:
                # This thread's own connection. Django only replaces a broken connection
                # between requests, so a fresh one each beat survives a dropped one
                # (and the pooler wants connections short anyway).
                connection.close()
