"""Pure submission checks (REQ-08; AC-09), independent of storage."""

from collections.abc import Collection
from datetime import datetime

from core.domain.statuses import ReportType
from cra_service.errors import Conflict, RuleViolation, field_error
from cra_service.timestamps import to_utc_second

PREVIOUS_REPORT: dict[ReportType, ReportType | None] = {
    "early_warning": None,
    "notification": "early_warning",
    "final_report": "notification",
}


def validate_submission(
    *,
    state: str,
    report_type: ReportType,
    aware_at: datetime | None,
    now: datetime,
    submitted_reports: Collection[ReportType],
    missing_fields: Collection[str],
    submitted_at: datetime | None = None,
) -> datetime:
    """Return the effective submission time, or reject without changing inputs.

    aware_at is None only for a ticket that never became reportable, which the state
    check rejects (409) before any time is read.

    The caller validates auth, resource/type existence and request syntax first.
    It supplies stored report types, the draft builder's Model C missing fields,
    and core.clock.now(). Unknown report types are internal integration errors;
    the route must reject unknown types and user_advisory with 404 beforehand.

    Success does not store or lock content, calculate statuses, or write audit.
    The caller must do those atomically after these checks. Q5 (agreed with
    Team 21, 2026-11-01): only the aware_at-to-now interval is checked, not
    chronology relative to a previous report's submitted_at.
    """
    if report_type not in PREVIOUS_REPORT:
        raise ValueError("unknown Article 14 report type")
    if state != "reportable":
        raise Conflict("Only a reportable ticket can record a submission.")
    if report_type in submitted_reports:
        raise Conflict("This report has already been submitted.")
    previous_report = PREVIOUS_REPORT[report_type]
    if previous_report is not None and previous_report not in submitted_reports:
        raise Conflict("The previous report must be submitted first.")

    aware_at = to_utc_second(aware_at)
    now = to_utc_second(now)
    effective_submitted_at = now if submitted_at is None else to_utc_second(submitted_at)
    errors = [field_error(field, "required for this report") for field in missing_fields]
    if not aware_at <= effective_submitted_at <= now:
        errors.append(field_error("submitted_at", "must be between aware_at and now"))
    if errors:
        raise RuleViolation(errors)
    return effective_submitted_at
