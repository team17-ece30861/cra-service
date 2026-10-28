# Handoff: Ann (API and Data)

**Last updated:** 2026-10-26 by Quincy's agent (Claude Code), from the Phase 4 kickoff with
Quincy. Ann's agent: rewrite this file in your own words at the end of your first session.

**For Ann's agent (Codex or other):** you're working for Ann, who owns API and Data on
Team 17. Read [`AGENTS.md`](../../AGENTS.md) and [`docs/plan.md`](../plan.md) before starting.
Restate the task to Ann before acting, and agree on behavior with Ann before writing code.

## Where things stand

Phase 4 is due **Sunday 2026-11-01**. Phase 3 is done: the ticket API (intake, get, list,
update, triage, audit) is live on Launchpad and Orbit and passes 55/55. None of the Phase
4 code exists yet.

**Phase 4 is split by feature** (Quincy, 2026-10-26): each person writes the rule in
`core/domain/`, the endpoint, and the tests for their own features. Richard has drafts,
recording submissions, and closing tickets. Ann has the pieces below. See
[Who builds what in Phase 4](../plan.md#who-builds-what-in-phase-4) and the day-by-day
[schedule](../plan.md#proposed-schedule). Quincy is building a web console on top of the
API and reviews every PR.

## Next up

1. **Mon 10-26: post the submission model's fields** in a PR description (one row per
   ticket and report type: `submitted_at`, `reference`, the locked `content` snapshot, the
   actor). Richard builds submission recording against it, so post it first.
2. **4.A1 (merged Tue 10-27):** the submission model and migration. Reset clears it
   automatically (it's in the `core` app). Quincy reviews the migration the same day.
3. **Statuses (4.D2, response part of 4.A5; Tue to Wed):** `submitted` if `submitted_at` ≤
   `due_at`, otherwise `submitted_late`, including the E6 boundary and a clock moved
   backward. Ticket responses show these, plus `submitted_at`, `reference`, and
   `next_due_at`.
4. **List filters and order (4.D5, filter part of 4.A5; Wed to Thu):** `state` and
   `obligation_status` filters on `GET /tickets` (bad values → 400). Order by
   `next_due_at` (the earliest unmet deadline), nulls last, ties per Q2.
5. **Acceptance cases for these features (Thu):** AC-06 and AC-11 in `acceptance/cases.py`.
   **Target: everything above merged by Thu 10-29**, so Launchpad can be tested Friday.
6. **4.A7 (Fri):** reporter confidentiality sweep (AC-16) across lists, drafts, audit
   entries, error bodies, and logs.
7. **3.9: contract freeze PR in `pod-k-shared`.** Bump `openapi.yaml`'s `info.version` from
   `0.1.0-draft`, record the agreed date in `info.description`, and get one approval from
   Team 21. Then mirror it into this repo's `openapi.yaml` and
   `pod-k-shared/team17/tester/openapi.yaml`. Quincy's email to Team 21 tells them the PR
   is coming.

## Alignment with Team 21 (as of 2026-10-26)

- The contract is still `0.1.0-draft`; nothing is frozen and Phase 4 operations aren't
  agreed.
- Quincy is sending Team 21 an email on 2026-10-27 with open questions Q1 to Q10
  (`docs/plan.md`), asking for answers by **noon Thu 10-29**. For any still open, build the
  proposal listed in the plan and note it in the PR. Q2 (list tie-break), Q4 (whether a
  later date change can flip a submitted report to late), and Q6 affect Ann's features
  directly.
- **Q6 changed on 2026-10-27** (Quincy and the team): a PATCH that changes nothing should
  succeed but add **no** audit entry. Today's code (`_audit` in `core/tickets.py`) adds one
  with an empty `changes` list, so the PATCH path needs to skip the entry when nothing
  changed. This changes the AC-12 counts.
- When a question is answered, log it in `docs/decisions.md`, remove it from the plan's
  table, and update `openapi.yaml` (all three copies) if the contract changes.

## Waiting on

- **Team 21:** answers to Q1 to Q10 and approval of the freeze PR.
- **Ann:** accept the invite to `team17-ece30861/pod-k-shared` (`zuo30`, still pending on
  2026-10-26). The freeze PR needs it.

## Notes for the next session

- Richard edits `core/tickets.py` too. Keep PRs small and merge often to limit conflicts.
- Set up locally with Python 3.12 and `docker compose up -d` (see `README.md`). Check
  with `pytest -q`, `ruff check . && ruff format --check .`, and
  `python manage.py makemigrations --check --dry-run`.
- 3.1 (reviewing the Phase 3 code Ann inherited) is lower priority than Phase 4 now.
- Never run `acceptance/` against Orbit. Team 17 tests on Launchpad; Orbit is for Team 21
  and the course staff.
