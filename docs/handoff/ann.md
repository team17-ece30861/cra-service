# Handoff: Ann (API and Data)

**Last updated:** 2026-11-22 by Quincy's agent (Claude Code): Phase 5 status and what's
left for Ann. Ann's agent: rewrite this file in your own words at the end of your next
session.

**For Ann's agent (Codex or other):** you're working for Ann, who owns API and Data on
Team 17. Read [`AGENTS.md`](../../AGENTS.md) and [`docs/plan.md`](../plan.md) before starting.
Restate the task to Ann before acting, and agree on behavior with Ann before writing code.

## Where things stand

- **5.5:** done. Ann's operations guide merged as #117 (`docs/operations.md`). Quincy's agent added
  fixes on 2026-11-22 (c9e3be4): a full access-log line, `HOST` and `NEW_TOKEN` set before
  use, the 5xx alert, the tester's one-run rule, and clearing a console lockout.
- **5.9:** done by Quincy's agent so Phase 5 could land: contract 0.3.0 with Q7, Q8 and Q9
  and the 422-lists-every-problem rule (#111, `pod-k-shared` #20), the 0.2.0 freeze
  (`pod-k-shared` #14, merged), and AC-13 (#113).
- Team 21 hasn't answered since 2026-11-01, so Team 17 decided Q7, Q8 and Q9 itself
  (see [`docs/decisions.md`](../decisions.md)); they reopen if Team 21 objects.

## In progress

- Nothing.

## Next up

1. **5.6 (spec part):** confirm the final spec version is contract 0.3.0 and `docs/spec.md`
   as merged; if Team 21 answers, carry their response into `pod-k-shared` #20.

## Waiting on

- **Team 21:** any reply on `pod-k-shared` #20.

## Notes for the next session

- Contract changes go through `pod-k-shared` first (a PR Team 21 approves), then get
  mirrored here. Changes to `openapi.yaml` here also need a human teammate's approval.
- Set up locally with Python 3.12 and `docker compose up -d` (see `README.md`). Check with
  `pytest -q`, `ruff check . && ruff format --check .`, and
  `python manage.py makemigrations --check --dry-run`.
- Team 17 tests on Launchpad; Orbit is for Team 21 and the course staff.
