# Handoff: Ann (API and Data)

**Last updated:** 2026-10-18 by Quincy's agent (Claude Code), from Quincy's notes. Ann's
agent: rewrite this file in your own words at the end of your first session.

**For Ann's agent (Codex or other):** you're working for Ann, who owns API and Data on
Team 17. Read [`AGENTS.md`](../../AGENTS.md) and [`docs/plan.md`](../plan.md) before starting.
Restate the task to Ann before acting, and agree on behavior with Ann before writing code.

## Where things stand

Phase 3 is due **2026-10-18**. Richard built the Phase 3 API and data layer (PR #7) so
Phase 3 wasn't blocked. It's merged to `main`, live on Orbit, and passed all 55 Phase 3
acceptance tests there on 2026-10-18. Ann now owns that code. API and Data needs no more
Phase 3 implementation. Two Phase 3 tasks are Ann's alone.

## Next up

1. **Task 3.9: freeze the Phase 3 contract with Team 21.** This one's deadline-critical.
   - Agree with Team 21 that the operations tagged `phase-3` in `openapi.yaml` won't
     change. Then bump `info.version` from `0.1.0-draft` and record the agreed date in
     `info.description`. Open a PR; a human approves it.
   - The shared copy of the contract will move to `team17-ece30861/pod-k-shared`. Changes
     there need approval from someone on Team 21.
   - In the same conversation with Team 21, raise these four open questions from
     `docs/plan.md`, and log the answers in `docs/decisions.md`:
     - **Q1:** a triage of `invalid` or `not_actively_exploited` that includes `aware_at`:
       accept, store, or reject? Today we accept it and drop it.
     - **Q7:** should `POST /tickets` reject a future `fix.available_at`? The contract
       lists no 422 for submit. Today we accept it.
     - **Q8:** the CRA starts the final-report clock when a corrective *or mitigating*
       measure is available [Art. 14(2)(c)]. Proposal: define `fix.available_at` as the
       first such measure (a wording change only). See `docs/reports/risk1-cra-review.md`.
     - **Q9:** the CRA requires early-warning Member States only "where applicable", but
       Model C requires `member_states` and `affected_versions` to record one. Keep it
       strict, or allow "unknown"?
2. **Task 3.1: review the merged code Ann now owns.** It's on `main`. Send fixes as small
   PRs to `main`, not a parallel API.

| File | What it does | Review focus |
|---|---|---|
| `core/schemas.py` | Request schemas for intake, update, triage | Fields, enums, lengths, and null versus omitted, against `openapi.yaml` |
| `core/models.py`, `core/migrations/0002_phase3_tickets.py` | `Ticket` (client fields in a JSON column) and `AuditEntry` | What's stored versus derived; audit `seq` uniqueness |
| `core/tickets.py` | Routes, response building, audit entries | Error order (404, 400, 409, 422), row locks, rollback, reporter privacy |
| `core/domain/` | Richard's pure deadline, status, and triage rules | Call them; don't re-implement rules in routes |
| `tests/test_phase3_api.py`, `acceptance/` | Local API tests and the shared acceptance cases | Add regression tests with any fix |

Already reviewed by Quincy's agent: one bug (PATCH re-checked a stored fix time), fixed
in PR #11. The known weak spot is thin PATCH test coverage.

## Waiting on

- **Team 21:** agreement for the contract freeze (3.9), and answers to Q1 and Q7.
- **Ann:** accept the invite to `team17-ece30861/pod-k-shared` (expected as `zuo30`; tell
  Quincy if that's not Ann's login).

## Notes for the next session

- Set up locally with Python 3.12 and `docker compose up -d` (see `README.md`). Check
  with `pytest -q`, `ruff check . && ruff format --check .`, and
  `python manage.py makemigrations --check --dry-run`.
- Phase 4 is where Ann's main building starts: drafts, submissions, close, list filters,
  and Schemathesis (tasks 4.A1 to 4.A8). Agree on function signatures with Richard in the
  first Phase 4 PR.
- Never run `acceptance/` against Orbit. Team 17 tests on Launchpad; Orbit is for Team 21
  and the course staff.
