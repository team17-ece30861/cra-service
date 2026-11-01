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

The integrated caller in `core/tickets.py` checks ticket state and passes parsed
timestamps. Triage rejects future awareness against `core.clock.now()`; updates
reject future awareness and fix availability. Intake follows the common create
schema without adding the update-only future-fix rule. Responses map the returned
values to each obligation's `due_at` and recalculate when either input changes.
The function reads no clock or database and mutates no ticket. It does not validate
triage, determine obligation statuses, or serialize HTTP responses; the API layer
handles those responsibilities.

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

The helper is explicitly for unsubmitted obligations. Recorded reports use
`submitted_report_status`: `submitted` if `submitted_at` <= `due_at` (UTC, whole
seconds), otherwise `submitted_late`, against the deadline from the ticket's current
data (Q4). It takes no clock. A final report whose deadline was cleared counts as on
time; a missing early-warning or notification deadline raises `ValueError`. `user_advisory` has no reporting obligation and is not passed
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
These are domain tests. The integration on this branch adds HTTP acceptance,
persistence, audit, and rollback checks in `tests/test_phase3_api.py` and the
portable cases in `acceptance/cases.py`. See [Phase 3 validation](phase3.md) for
the requirement mapping, recorded results, and deployment work still pending.

## Phase 4 report draft content

`core.domain.drafts.build_draft` implements Model C's field selection and
completeness rules for `early_warning`, `notification`, `final_report`, and
`user_advisory`. Call it with keyword arguments `report_type`, `ticket_id`,
`aware_at`, and `ticket_fields` (the already validated, nested ticket fields).
It returns a `DraftResult` with `content` and `missing_fields`.

Content contains `ticket_id` and UTC-to-the-second `aware_at`, plus only the
nonempty fields allowed for that report type. Nested fields keep their ticket
structure, such as `product.name` and `mitigations.for_users`. Fix availability
timestamps are normalized to UTC seconds as well. Required fields that are
absent, null, empty strings, or empty lists appear in `missing_fields` using
dotted paths, in Model C row order. Optional fields never block completeness.
Countries and affected versions remain required for early warnings under the
published contract; the proposed Q9 relaxation has not been approved.

The function copies selected values individually, so it cannot include reporter
details or unlisted fields nested inside an allowed object. Building or editing
the returned draft does not mutate the ticket or any other draft. It reads no
database or service clock and accepts timezone-aware datetimes. Unknown report
types raise `ValueError` at this internal boundary; the HTTP caller must map
unknown client report types to 404 before invoking it.

`tests/test_drafts.py` establishes expected field selections and missing-field
lists from Model C, independently of the code. It checks each required field, incremental
completion (including one fill order checked against all four drafts), cleared sections, optional fields, exclusion of reporter/unlisted
data, UTC normalization, and independence from mutable inputs.

The pure generator (4.D1) is merged in PR #75. Ann's recorded-report foundation
and status helper are merged through Quincy's reconciliation in PR #76. This
4.A2 increment preserves their model, helper, migration and original tests.

## Draft read endpoint (4.A2)

`GET /tickets/{id}/reports/{type}` returns the existing Draft envelope. Unknown
types/tickets return 404. Under Q3's documented proposal, never-reportable tickets
return 409 and resolved tickets remain readable. Before recording, Model C builds
live content/missing fields; a stored submission instead supplies locked content,
time/reference and empty missing fields. Metadata uses current deadlines under Q4.
Both proposals remain open pod questions, not new contract agreements.

Advisory is always live, with null status/deadline/submission/reference. Auth is
required but X-Actor is not. Reads add no writes/audit and exclude reporter data.
The route uses main's stricter submitted helper only for actual recorded rows;
missing early/notification deadlines remain integration errors.

Portable cases cover Model C, incremental completeness, read-only behavior, time
boundaries, auth, unknown paths and state conflicts. Local stored fixtures test
locked reads, current-deadline recalculation and resolved tickets; they are not
evidence of working submission POST, audits, closure or concurrency. Supplemental
upgrade/reset/model/helper tests exercise the merged foundation without changing it.
Local focused validation: 310 passed on SQLite; PostgreSQL/deployed validation
and posted independent PR approval remain pending. Ann's 4.A5 remains separate.

## Submission validation rule (4.D3)
`core.domain.submissions.validate_submission` (4.D3) is pure: it receives state,
report type, awareness/recording time, submitted identities, Model C missing paths
and optional submitted time. State/duplicate/predecessor conflicts (409) precede
missing fields or interval violations (422). It returns UTC seconds, defaults to
the supplied now and changes no input. Q5 adds no timestamp ordering between
reports beyond the inclusive aware-to-now interval. Sixty unit tests cover this;
the actual recording endpoint/audit/transactions remain separate task 4.A3.

## Submission recording endpoint (4.A3)
`POST /tickets/{id}/reports/{type}/submission` (4.A3) records an external
submission, not a report sent to a regulator. Only the three regulatory report
types record; unknown/advisory types and unknown tickets return 404 before actor/
schema errors. The strict optional body allows submitted_at/reference only;
absent means an empty object, explicit null or unknown fields return 400.

The route locks the ticket, calls 4.D3 with Model C missing paths and one explicit
clock value, then stores generated content, normalized time/actor and reference
in the merged model. One report_submitted audit records reports.<type> from null
to the safe snapshot/time/reference/actor, at recording now. It returns the locked
Draft. The outer POST transaction covers snapshot, audit and rendering; a nested
savepoint permits uniqueness fallback without querying a broken transaction.
Other IntegrityErrors are not disguised as conflicts. Failed writes/rendering
roll back; duplicate/order 409 precede fields/time 422. PostgreSQL race CI remains
needed. Ann's Ticket/list statuses/metadata/next_due_at (4.A5) remain separate.

## Closure validation rule (4.D4)

`core.domain.closure.close_ticket` requires reportable state and actual early
warning, notification and final report identities, otherwise 409. It returns
immutable closed/resolved changes, reads no clock/database and mutates no input.
Current time or subsequently incomplete drafts add no closure condition. Advisory
cannot replace a required report. Thirty tests cover all report subsets, states
and input/result safety. Actual HTTP persistence/audit remain separate task 4.A4.

## Closure endpoint and lifecycle (4.A4)

The bodyless `POST /tickets/{id}/close` locks/looks up the ticket (404), validates
X-Actor (400), then calls 4.D4 (state/report-set 409). It saves closed/resolved and
one closed audit: old/new state/resolution, normalized actor, one clock and null
reason. Existing middleware makes state/audit/response atomic; injected failures
roll back without sequence gaps. Shared ticket locking serializes existing writers.

Closed tickets reject edits, triage, submissions and repeat closure. Ticket/list/
audit and all four resolved draft reads stay available; snapshots are unchanged.
Close/audit omit reporter fields. Thirty-four portable closure/AC-12 cases and
eleven local storage/fault/concurrency cases supplement the rule. Genuine duplicate
close and final-recording/close races require PostgreSQL. AC-12 changes a real
title, not unsettled Q6 no-op behavior, and checks actors/times/seq and audit 405s.

Combined focused local regression: 711 passed/four PostgreSQL skips. Complete
localhost HTTP: 182 passed, one Windows 10053 connection abort reading an early
oversized-request 401, one skip. The same abort reproduced in minimal unframed
WSGI without CRA/Django; no swallowing/retry-until-green hides it. CI/review and
actual-stack validation remain gates; Ann's 4.A5 is not implemented by this task.

## Contract documentation gap



The current `openapi.yaml` references REQ-04 and exposes obligation deadlines,
but does not spell out the hour/day intervals or the fix-before-awareness rule.
The calculation above is specified in the supplied Phase 2 report, REQ-04 and
Model D, and matches Richard's project handoff. The gap is in the standalone
OpenAPI description, rather than an unresolved choice of arithmetic. Any update
to the shared OpenAPI file should follow the pod's agreement process.
