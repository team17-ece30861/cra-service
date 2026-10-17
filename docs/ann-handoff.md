# Ann: API + Data handoff

This guide is a dated handoff for Ann and her coding assistant, prepared on
2026-10-14. Inspect the current checkout and teammate changes before using it.
It describes the implementation in
[PR #7](https://github.com/team17-ece30861/cra-service/pull/7), on
`codex/phase3-acceptance`; it is not evidence that the increment is on `main`
or deployed.

## Where to start

Ann owns API + Data. Richard owns Domain Logic + Testing, and Quincy coordinates
platform/deployment work. Richard was authorized to add a minimal API/data layer
while Ann's implementation was not yet available, so Phase 3 could be integrated
and tested. Ann should review and take ownership of that existing layer, not
rebuild it from a platform-only checkout. These responsibilities do not imply
that Ann has already reviewed or approved the starter implementation.

**The first task is Phase 3 API/data review, not starting the Phase 4 reporting
workflow.** If the implementation is acceptable, there may be no further Phase 3
API coding needed before team review, release, and deployed validation. Fix
verified gaps with focused changes rather than introducing a parallel ticket API.

Read these in order:

1. `README.md` and `CLAUDE.md`: setup, repository rules, and deployment workflow.
2. [Phase 3 validation](phase3.md): delivered behavior, operation status, models,
   acceptance coverage, and recorded validation.
3. `openapi.yaml`: common request/response schemas and observable behavior.
   Ninja's generated `/docs` is not the contract.
4. [Domain interfaces](domain.md) and [triage rules](triage.md): Richard's pure
   helpers and the integration boundary.
5. The implementation and tests listed below. Existing code may be newer than
   this handoff; preserve unrelated teammate work.

## Get the right baseline

Start with `git status --short --branch`. Preserve uncommitted work; do not reset,
force-checkout, or overwrite it to follow these examples.

If PR #7 is still unmerged, review `origin/codex/phase3-acceptance`. For edits in a
separate clean checkout, one possible branch workflow is:

```bash
git fetch origin
git switch --no-track -c codex/ann-phase3-review origin/codex/phase3-acceptance
```

If that local branch already exists, inspect it and switch to it rather than
forcing its recreation. After PR #7 is merged, start new work from updated
`origin/main` instead. Coordinate dependent branches before opening another PR
that contains all of PR #7's changes. Never push directly to `main`.

PR #7 already includes the domain changes from PRs #5 and #6. Do not cherry-pick
or merge those again into the integration branch. Opening only `main` before
the integration is merged can make the ticket implementation appear absent.

## Implementation map

| File | Purpose | Ann's review focus |
| --- | --- | --- |
| `core/schemas.py` | Strict intake, update, triage, and nested request schemas. | Match common fields, enums, lengths, timestamps, omitted/null behavior, and unknown-field rejection. |
| `core/models.py` | `Ticket`, `AuditEntry`, and the existing `FixedClock`. | Persisted versus derived data, audit association, sequence uniqueness. |
| `core/migrations/0002_phase3_tickets.py` | Adds ticket and audit tables after `0001_initial`. | Clean PostgreSQL migration and compatibility with the existing clock table. |
| `core/tickets.py` | Ticket routes, database access, response assembly, updates, and audits. | Contract behavior, locking, rollback, privacy, and exactly one audit per successful mutation. |
| `cra_service/api.py` | Registers the ticket router at `/tickets`. | Extend the existing API rather than creating another API object. |
| `core/domain/deadlines.py` | Pure deadline calculation returning `Deadlines`. | Call it; coordinate rule changes with Richard. |
| `core/domain/statuses.py` | Pure statuses for unsubmitted obligations. | Supply a single explicit service-clock value per response; do not use it for submitted reports. |
| `core/domain/triage.py` | Pure triage returning `TriageResult` or existing errors. | Supply parsed inputs and apply the returned changes transactionally. |
| `cra_service/validation.py`, `timestamps.py`, `errors.py`, `middleware.py` | Existing parsing, error, authentication, body-size, and request-transaction infrastructure. | Reuse it; do not bypass it or duplicate it. |
| `tests/test_phase3_api.py` | Database/API integration, rollback, audit/privacy, and concurrency checks. | Add focused regression cases alongside behavior changes. |
| `acceptance/cases.py`, `client.py`, `conftest.py` | Shared acceptance cases, OpenAPI response validation, external runner/reporting. | Keep observable expectations aligned with the common contract. |

## Already implemented

- Intake with a unique UUID, state `received`, and receipt time from the service
  clock; strict client-input validation and one `created` audit entry.
- Single-ticket detail, an unfiltered deadline-ordered list, and editable details
  through PATCH. Reporter data is returned only by single-ticket detail.
- Triage to `reportable`, or closure as `invalid` / `not_actively_exploited`;
  missing/future awareness and repeat triage rejection.
- Early-warning, notification, and final-report deadlines, plus initial
  `not_applicable`, `awaiting_fix`, `pending`, and `overdue` statuses on reads.
- Awareness/fix update checks, awareness change reasons, deadline recalculation,
  nested-object merge, list replacement, and supported optional-field clearing.
- Audit reads, successful mutation records, closed-ticket update rejection,
  error precedence, rollback, and a PostgreSQL concurrent-triage regression test.
- Integration with existing bearer authentication, actor validation, reset, and
  persistent fixed-clock controls. Deployment workflows were not changed.

## Boundary to preserve

Richard's domain helpers take plain values, not Django models. They read no
database, do not obtain the current time themselves, and do not mutate tickets:

```text
calculate_deadlines(aware_at, fix_available_at=None) -> Deadlines
unsubmitted_obligation_status(*, report_type, applicable, due_at, now) -> str
triage_ticket(*, state, decision, now, aware_at=None) -> TriageResult
```

These are interface summaries; use the actual type definitions in the modules.
Ann's API/data layer owns loading data, parsing request schemas, calling the
helpers, assembling responses, and persisting successful changes/audits. Reuse
the existing exception handlers for `BadRequest`, `NotFound`, `Conflict`, and
`RuleViolation`. Pure business-rule changes and their tests should be coordinated
with Richard rather than duplicated inside routes.

`Ticket` persists state, resolution, receipt/awareness times, and validated client
fields in `data` (JSON). Deadlines and initial obligation statuses are derived
on reads, not independently stored. There is no report-submission/snapshot model
yet. `AuditEntry` records per-ticket sequence, time, actor, action, changes, and
reason, with a unique `(ticket, seq)` constraint.

For triage/update, the existing flow is: look up and lock the ticket, validate,
call the domain rules or stage updated values, render/check the resulting
response, save, and append one audit entry. `PlatformMiddleware` wraps writes in
a transaction and rolls it back for error responses. Preserve row locking and
rollback behavior; catching an error must not accidentally commit partial writes.
Creation also relies on the request transaction for its ticket/audit writes.

Validation distinguishes omitted fields from explicit nulls. Do not convert
every optional input to a nullable field: compare the exact OpenAPI schema.
The existing serialization uses `exclude_unset=True` for this distinction.
Ticket responses currently use dictionaries; acceptance tests validate their
shape against `openapi.yaml`, not generated Ninja response schemas.

## Ann's Phase 3 checklist

1. Verify the checkout contains the integrated code and read PR #7's diff. Review
   schemas, models, migration, ticket routes, and router registration first.
2. Run the local PostgreSQL setup and checks below. Confirm migrations work on
   a fresh local database; do not edit an applied migration on a shared database.
3. Compare Phase 3 operations and relevant failure paths against `openapi.yaml`.
   Check missing/unknown fields, malformed timestamps, correct status codes,
   reporter exclusion, and no database/audit changes after rejected requests.
4. Review JSON-field storage, update semantics, and response assembly. Raise any
   concrete maintainability or contract issue with a focused proposed fix; a
   complete model/schema rewrite is not required just to begin ownership.
5. Confirm the triage ambiguity below with Richard/Quincy and the pod. Do not
   silently rewrite the shared contract or tests to resolve it.
6. Add regression tests for approved fixes and update the operation/limitation
   record in `docs/phase3.md`. Coordinate review/merge/deployment with Quincy and
   deployed/cross-team acceptance testing with Richard.

Phase 3 review is complete when Ann has reviewed the API/data changes, any
agreed blockers are fixed and tested, and remaining limitations are accurately
documented. That is separate from claiming the whole phase has been deployed.

## Known limits and later work

| Area | Current state | Next responsibility when scheduled |
| --- | --- | --- |
| Non-reportable triage with optional `aware_at` | API returns absent reporting awareness; the contract does not explicitly settle retention of that input. | Pod clarification before changing response/audit expectations. |
| Deadline arithmetic documentation | Phase 2 Model D supplies the intervals; standalone OpenAPI prose is less explicit. | Coordinate any shared-contract clarification, not an arithmetic redesign. |
| `GET /tickets` filters | Only the unfiltered Phase 3 list is implemented; `state` and `obligation_status` filtering is not. | Ann's later query/API integration with Richard's tests. |
| Report drafts / `missing_fields` | Not implemented. | Richard's agreed completeness/domain rules; Ann's route and response wiring. |
| Report submissions, locked content, `submitted` / `submitted_late` | No persisted submission data or success endpoints yet. | Agree the data/domain boundary first; Ann models/wiring, Richard ordering/status rules and tests. |
| Reportable closure as `resolved` | Not implemented; non-reportable closure during triage already works. | Richard's closure rules and Ann's endpoint/persistence, after submissions exist. |
| Persistence across restart and performance at 1,000 tickets | Not demonstrated by the recorded runs. | Plan the relevant validation rather than assuming table creation proves either. |
| Deployed HTTPS and Team 21 tests | Pending for this increment. | Quincy release coordination; Richard testing with team support. |

The common operation table in `docs/phase3.md` is the detailed status record.
Later reporting features are not prerequisites for beginning this Phase 3 review.
Do not infer complete Phase 4 support from the existing PATCH/audit endpoints.

## Verification

Use Python 3.12, the development requirements, and local PostgreSQL 18 as described
in `README.md` and `.env.example`. Load the environment for the shell in use;
Django settings do not automatically load `.env`. Run against a local development
database, not a shared Neon/evaluation database:

```bash
python manage.py migrate
python manage.py check
python manage.py makemigrations --check --dry-run
python -m pytest -q tests/test_phase3_api.py tests/test_contract_validator.py
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
```

Linux CI with PostgreSQL is the supported full-suite reference. Windows cannot
run the Unix-only Gunicorn access-log tests unchanged, and SQLite skips the
PostgreSQL row-lock test; do not remove tests or mistake those exclusions for a
complete supported-environment run.

Recorded implementation CI at `6c8d8a7` passed 513 tests plus lint, migration, and
Django checks. The earlier local external HTTP run passed 54 cases and skipped
the HTTPS-only probe. See `docs/phase3.md` for exact revisions and evidence. These
results are a baseline, not a guarantee that a new edit is correct.

The portable suite in `acceptance/` resets the target before each case and changes
its clock. Do not run it against a shared deployment without a coordinated reset
window and permission; never paste tokens into an AI conversation or commit them.
Normal `pytest -q` collects `tests/`, not the destructive remote suite.

## Starter prompt for Ann's coding assistant

Use this prompt with the repository checkout, not just an isolated copy of this
document. Replace the starting branch if PR #7 has since been merged.

```text
I am Ann, responsible for API + Data on Team 17's CRA service. Richard owns
Domain Logic + Testing; Quincy coordinates platform/deployment work.

First inspect git status and the current branch. Read docs/ann-handoff.md,
README.md, CLAUDE.md, docs/phase3.md, openapi.yaml, docs/domain.md, and
docs/triage.md. Then inspect core/schemas.py, core/models.py, the migrations,
core/tickets.py, cra_service/api.py, the shared validation/middleware/error
utilities, and tests/test_phase3_api.py.

Our Phase 3 integration is in PR #7, branch codex/phase3-acceptance, unless it
has already merged. It includes starter API/data code as well as Richard's
domain work; do not recreate those modules or cherry-pick PRs #5/#6 again.
Treat the handoff as dated context and preserve newer teammate changes.

Do not edit files yet. Explain what API/data work already exists, identify
any verified Phase 3 gaps with file references and contract evidence, and
propose the smallest next review/fix task for my role. Separate Phase 3
review/release blockers from optional refactoring and Phase 4 features.

Keep domain rules pure, reuse the existing clock/errors/transactions, preserve
reporter privacy and failed-request rollback, and do not change the shared
contract or deployment workflows without coordination. Do not merge, deploy,
run destructive remote tests, or handle shared tokens as part of this review.
```
