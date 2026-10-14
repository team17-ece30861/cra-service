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
5. Apply the returned changes in memory and build the response with derived
   deadlines and obligations, rejecting out-of-range deadlines before saving.
6. Save the ticket and append exactly one `triaged` audit entry in the same
   successful transaction, retaining the actor and request reason.

`core/tickets.py` implements this sequence on the integration branch.

Missing awareness for an actively-exploited decision raises the existing
`BadRequest` (400). Triage outside `received` raises `Conflict` (409). Future
awareness raises `RuleViolation` (422). Checks follow 400 before 409 before 422.
An awareness time equal to now is accepted, as is one earlier than receipt.
Times are normalized to UTC and fractional seconds truncated before comparison.

Active exploitation returns `reportable`, a null resolution, and the normalized
awareness time. The API passes this awareness time to the deadline helper from
PR #5. `not_actively_exploited` and `invalid` return `closed` with
the corresponding resolution and no reporting awareness time. The caller must
return `not_applicable` obligations for those closed tickets.

## Acceptance coverage

- AC-04: unit tests cover absent awareness (400), future awareness (422), and
  repeat triage (409), including error precedence. The integrated request schema
  and API tests additionally cover missing reason (400) and unchanged stored data.
- AC-05: both non-reportable decisions close with the matching resolution and
  reject further triage. Integrated acceptance tests also cover rejected updates,
  read access after closure, and `not_applicable` response obligations.
- AC-03/AC-14: tests cover acceptance of awareness before triage, UTC-offset
  normalization, and truncation. Integrated service tests verify exact Model D
  E1-E5 deadlines and the initial obligation statuses.

The current contract allows an optional `aware_at` on any triage request but
does not say whether a non-reportable decision should retain such an input.
The result describes reporting awareness only, which is absent for those
decisions. The integrated API uses that absent reporting awareness; confirm this
interpretation with the pod before claiming shared agreement on the extra input.

The original domain tests require no database and PR #6 supplies only domain
logic. The combined integration PR #7 implements the ticket endpoint, persistence,
and audit behavior. See [Phase 3 validation](phase3.md) for coverage and recorded
test results. Review, merge, deployment, and cross-team validation remain pending.
