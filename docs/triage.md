# Triage domain integration

`core.domain.triage.triage_ticket` implements the state and awareness-time rules
for REQ-02 and REQ-03 from the Phase 2 specification and the common OpenAPI triage
operation. It receives `state`, a triage `decision`, optional `aware_at`, and an
explicit `now`, all as keyword arguments. Datetimes must be timezone-aware.
The result is an immutable `TriageResult` containing `state`, `resolution`, and
`aware_at`; the function performs no database writes or clock reads.

## API integration order

1. Authenticate and enforce the request-body size limit (existing middleware).
2. Load the ticket, returning 404 if it does not exist.
3. Require `X-Actor` and validate the body using the existing request-validation
   utilities. The decision must be one of the three common contract values;
   `reason` is required and must satisfy the `LongText` schema. Unknown fields
   and invalid timestamp strings return 400 at this boundary.
4. Call `triage_ticket`, supplying `now=core.clock.now()` and parsed timestamps.
5. Apply the returned changes and append exactly one `triaged` audit entry in
   the same successful transaction, retaining the actor and request reason.
6. Build the response with the appropriate derived deadlines and obligations.

Missing awareness for an actively-exploited decision raises the existing
`BadRequest` (400). Triage outside `received` raises `Conflict` (409). Future
awareness raises `RuleViolation` (422). Checks follow 400 before 409 before 422.
An awareness time equal to now is accepted, as is one earlier than receipt.
Times are normalized to UTC and fractional seconds truncated before comparison.

Active exploitation returns `reportable`, a null resolution, and the normalized
awareness time. Pass this awareness time to the deadline helper from PR #5 when
integrating that work. `not_actively_exploited` and `invalid` return `closed` with
the corresponding resolution and no reporting awareness time. The caller must
return `not_applicable` obligations for those closed tickets.

## Acceptance coverage

- AC-04: unit tests cover absent awareness (400), future awareness (422), and
  repeat triage (409), including error precedence. Missing reason (400) remains
  the responsibility of the request schema and its API tests.
- AC-05: both non-reportable decisions close with the matching resolution and
  reject further triage. Rejecting updates, read access after closure, and
  `not_applicable` response obligations still require API integration tests.
- AC-03/AC-14: tests cover acceptance of awareness before triage, UTC-offset
  normalization, and truncation. Full Model D deadline/status verification
  remains part of the integrated service tests.

The current contract allows an optional `aware_at` on any triage request but
does not say whether a non-reportable decision should retain such an input.
The result describes reporting awareness only, which is absent for those
decisions. The API layer should resolve handling of the extra input with the
pod before asserting a response or audit behavior for that case.

These tests require no database. This PR supplies domain logic; it does not
implement or deploy the ticket endpoint.
