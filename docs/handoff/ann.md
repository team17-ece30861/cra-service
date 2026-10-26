# Handoff: Ann (API and Data)

**Last updated:** 2026-10-26 by Quincy's agent (Claude Code), from the Phase 4 kickoff with
Quincy. Ann's agent: rewrite this file in your own words at the end of your first session.

**For Ann's agent (Codex or other):** you're working for Ann, who owns API and Data on
Team 17. Read [`AGENTS.md`](../../AGENTS.md) and [`docs/plan.md`](../plan.md) before starting.
Restate the task to Ann before acting, and agree on behavior with Ann before writing code.

## Where things stand

Phase 4 is due **Sunday 2026-11-01**. Phase 3 is done: the ticket API (intake, get, list,
update, triage, audit) is live on Launchpad and Orbit and passes 55/55. Ann owns that code.
Phase 4 is Ann's main build: report drafts, submissions, close, and list filters. None of
it exists yet. The day-by-day schedule is in
[`docs/plan.md`](../plan.md#proposed-schedule).

At the kickoff, Quincy took on a web console that sits on top of the API (4.U1 to U4), so
Quincy won't be adding API work. Schemathesis (4.A6) has been offered to Richard to
lighten Ann's load; Richard hasn't answered yet.

## Next up

1. **4.A1 (Mon to Tue):** the submission model and migration. One row per ticket and
   report type, with `submitted_at`, `reference`, the locked `content` snapshot, and the
   actor. Reset clears it automatically (it's in the `core` app).
2. **4.A5 (Tue):** `state` and `obligation_status` filters on `GET /tickets` (bad values →
   400), and ticket responses that use submissions for statuses, `submitted_at`,
   `reference`, and `next_due_at`.
3. **4.A2 to A4 (Wed to Thu):** the draft read, submission, and close endpoints, built on
   Richard's rules in `core/domain/`. Richard posts the function signatures in a PR
   description on Mon 10-26; build against those. **Target: all of 4.A1 to A5 merged by
   Thu 10-29**, so Launchpad can be tested Friday and Quincy can launch Orbit.
4. **4.A7 (Fri):** reporter confidentiality sweep across lists, drafts, audit entries,
   error bodies, and logs.
5. **3.9: contract freeze PR in `pod-k-shared`.** Bump `openapi.yaml`'s `info.version` from
   `0.1.0-draft`, record the agreed date in `info.description`, and get one approval from
   Team 21. Then mirror it into this repo's `openapi.yaml` and
   `pod-k-shared/team17/tester/openapi.yaml`. Quincy's email to Team 21 tells them the PR
   is coming.

## Alignment with Team 21 (as of 2026-10-26)

- The contract is still `0.1.0-draft`; nothing is frozen and Phase 4 operations aren't
  agreed.
- Quincy is sending Team 21 an email on 2026-10-26 with open questions Q1 to Q10 (`docs/plan.md`),
  asking for answers by **Wed 10-28**. For any still open, we build the proposal listed in
  the plan and say so in the report. Q3 (drafts for never-reportable tickets), Q4
  (whether a late date change can flip a submitted report to late), and Q6 (a no-change
  PATCH still logs an audit entry) affect Ann's endpoints directly.
- When a question is answered, log it in `docs/decisions.md`, remove it from the plan's
  table, and update `openapi.yaml` (both copies) if the contract changes.

## Waiting on

- **Richard:** the 4.D1 to D5 function signatures (Mon) and rules (merged by Wed).
- **Team 21:** answers to Q1 to Q10 and approval of the freeze PR.
- **Ann:** accept the invite to `team17-ece30861/pod-k-shared` (`zuo30`, still pending on
  2026-10-26).

## Notes for the next session

- Set up locally with Python 3.12 and `docker compose up -d` (see `README.md`). Check
  with `pytest -q`, `ruff check . && ruff format --check .`, and
  `python manage.py makemigrations --check --dry-run`.
- 3.1 (reviewing the Phase 3 code Ann inherited) is lower priority than Phase 4 now. Fix
  anything found as small PRs to `main`.
- Never run `acceptance/` against Orbit. Team 17 tests on Launchpad; Orbit is for Team 21
  and the course staff.
