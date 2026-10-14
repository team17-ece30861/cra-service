# Domain logic integration

## Deadline calculation

`core.domain.deadlines.calculate_deadlines(aware_at, fix_available_at=None)`
accepts timezone-aware Python datetimes and returns an immutable `Deadlines`
value with `early_warning_due`, `notification_due`, and `final_report_due`.
All returned timestamps are UTC with fractional seconds truncated, using the
existing timestamp helper (AC-14).

The rules in Richard's project handoff are:

- Early warning: awareness plus 24 elapsed hours.
- Notification: awareness plus 72 elapsed hours.
- Final report: the later of awareness and fix availability plus 14 elapsed days.
- Without a fix availability timestamp, the final deadline is `None`.

These rules cover the REQ-04 calculation and the recalculation described by the
update operation (AC-05, AC-07). No weekend, holiday, or daylight-saving adjustment
applies.

The API/data caller checks ticket state, validates that awareness and fix times
are not in the future against `core.clock.now()`, and passes parsed timestamps.
Map the returned values to each obligation's `due_at` and recalculate when either
input changes. The function reads no clock or database and mutates no ticket.
It does not validate triage, determine obligation statuses, or serialize HTTP
responses. Those are separate integration steps.

## Contract documentation gap

The current `openapi.yaml` references REQ-04 and exposes obligation deadlines,
but does not spell out the hour/day intervals or the fix-before-awareness rule.
The calculation above follows the supplied project handoff. The pod should
confirm and document these rules in the shared specification before cross-team
acceptance testing; this change does not alter the common API contract.
