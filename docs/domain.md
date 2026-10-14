# Domain logic integration

## Deadline calculation

`core.domain.deadlines.calculate_deadlines(aware_at, fix_available_at=None)`
accepts timezone-aware Python datetimes and returns an immutable `Deadlines`
value with `early_warning_due`, `notification_due`, and `final_report_due`.
All returned timestamps are UTC with fractional seconds truncated, using the
existing timestamp helper (AC-14).

The rules in the agreed Phase 2 specification, Q3.1 REQ-04 and Q3.2 Model D, are:

- Early warning: awareness plus 24 elapsed hours.
- Notification: awareness plus 72 elapsed hours.
- Final report: the later of awareness and fix availability plus 14 elapsed days.
- Without a fix availability timestamp, the final deadline is `None`.

These rules cover the REQ-04 calculation checked by AC-03 and the timestamp
normalization checked by AC-14. Calling the helper again supports the deadline
recalculation required by REQ-06/AC-07; that full criterion also needs API validation
and audit behavior. AC-05 covers non-reportable closure, not deadline calculation.
No weekend, holiday, or daylight-saving adjustment applies.

The API/data caller checks ticket state, validates that awareness and fix times
are not in the future against `core.clock.now()`, and passes parsed timestamps.
Map the returned values to each obligation's `due_at` and recalculate when either
input changes. The function reads no clock or database and mutates no ticket.
It does not validate triage, determine obligation statuses, or serialize HTTP
responses. Those are separate integration steps.

## Contract documentation gap

The current `openapi.yaml` references REQ-04 and exposes obligation deadlines,
but does not spell out the hour/day intervals or the fix-before-awareness rule.
The calculation above is specified in the supplied Phase 2 report, REQ-04 and
Model D, and matches Richard's project handoff. The gap is in the standalone
OpenAPI description, rather than an unresolved choice of arithmetic. Any update
to the shared OpenAPI file should follow the pod's agreement process.
