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

## Initial obligation statuses

`core.domain.statuses.unsubmitted_obligation_status` derives the four statuses
needed before submission recording is implemented. Its keyword arguments are
`report_type`, `applicable`, `due_at`, and an explicit `now`:

- An obligation that does not apply is `not_applicable`.
- An applicable final report without a fix deadline is `awaiting_fix`.
- An applicable, unsubmitted report at or before its deadline is `pending`.
- An applicable, unsubmitted report after its deadline is `overdue`.

Use the same `core.clock.now()` value for all three obligations in a response.
Pass `applicable=False` for received tickets and tickets triaged as invalid or
not actively exploited. Derive applicability from the reporting history rather
than just `state == "reportable"` when extending this to later phases: resolving
a reportable ticket must not discard its submission history.

Pass the calculated deadline for the chosen report. A missing deadline is valid
only for an applicable final report; missing early-warning/notification deadlines
and unknown report types raise `ValueError` as internal integration errors.
Validate client input at the API boundary before calling this helper. It reads
no database or clock and does not store status. Repeating it with a changed
clock or deadline immediately changes the derived result.

The helper is explicitly for unsubmitted obligations. It cannot determine
`submitted` or `submitted_late`; the later submission workflow must handle those
reports separately. `user_advisory` has no reporting obligation and is not passed
to this function.

## Shared example coverage

`tests/fixtures/phase3_model_d.json` records the exact published E1-E5 inputs and
expected deadlines from Phase 2 Model D, plus the E1 early-warning/notification
statuses. `tests/test_model_d.py` compares domain outputs to those fixed values
instead of generating expected deadlines from the calculation under test.

`tests/test_statuses.py` checks the Model B status rules, including Model D E6's
exact due-time versus one-second-late boundary, clock movement backward, UTC
offsets, and truncation. Together these support AC-03, the non-applicability part
of AC-05, AC-14 normalization, and the unsubmitted boundary part of AC-06.
They are domain tests; full HTTP acceptance, persistence, and audit verification
remain pending API integration.

## Contract documentation gap

The current `openapi.yaml` references REQ-04 and exposes obligation deadlines,
but does not spell out the hour/day intervals or the fix-before-awareness rule.
The calculation above is specified in the supplied Phase 2 report, REQ-04 and
Model D, and matches Richard's project handoff. The gap is in the standalone
OpenAPI description, rather than an unresolved choice of arithmetic. Any update
to the shared OpenAPI file should follow the pod's agreement process.
