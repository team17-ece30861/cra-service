# Handoff: Ann (API and Data)

**Last updated:** 2026-11-01 by Quincy's agent (Claude Code), handing over Ann's Phase 5
tasks. Ann's agent: rewrite this file in your own words at the end of your next session.

**For Ann's agent (Codex or other):** you're working for Ann, who owns API and Data on
Team 17. Read [`AGENTS.md`](../../AGENTS.md) and [`docs/plan.md`](../plan.md) before starting.
Restate the task to Ann before acting, and agree on behavior with Ann before writing code.

## Where things stand

Phase 4 is delivered and released to Orbit (2026-11-01). The API and Data pieces are done:
the recorded-report table and submitted statuses (PR #76), statuses in ticket responses
plus list filters and order (PR #84), and the reporter confidentiality sweep (PR #88). The
contract freeze PR is open in `pod-k-shared` (#14) and waiting on Team 21's approval.
Team 21 agreed to Q1 to Q6 and Q10 on 2026-11-01; Q7 and Q9 are agreed in principle but
need contract changes; Q8 is unanswered (see [`docs/decisions.md`](../decisions.md)).

## In progress

- Nothing of Ann's. `pod-k-shared` #14 (the freeze) is open; see Waiting on.

## Next up (Phase 5, split agreed 2026-11-01)

1. **5.9, contract and API:**
   - Q7: a `pod-k-shared` PR adding a 422 to submit for a future `fix.available_at`,
     approved by Team 21, then the code and tests here.
   - Q9: settle the exact form of "unknown" member states (and whether affected versions
     too) with Team 21, then the contract PR, the code, and the Model C table in the spec.
   - Q8: raise it with Team 21 and word the answer into the spec.
   - Once #14 merges: mirror the frozen `openapi.yaml` into this repo and
     `pod-k-shared/team17/tester/openapi.yaml` (the three copies must match).
   - Our own AC-13 run: Schemathesis against `openapi.yaml`, at least 500 generated
     malformed requests, no 5xx, data unchanged.
2. **5.5:** a short operations guide, mostly a trim of [`docs/platform.md`](../platform.md).
3. **5.6 (spec part):** the final spec version agreed with Team 21.

## Waiting on

- **Team 21:** approval of `pod-k-shared` #14, and an answer to Q8.
- **Ann:** accept the invite to `team17-ece30861/pod-k-shared` (`zuo30`, still pending on
  2026-11-01). Contract PRs need it.

## Notes for the next session

- Contract changes go through `pod-k-shared` first (a PR Team 21 approves), then get
  mirrored here. Changes to `openapi.yaml` here also need a human teammate's approval.
- Set up locally with Python 3.12 and `docker compose up -d` (see `README.md`). Check with
  `pytest -q`, `ruff check . && ruff format --check .`, and
  `python manage.py makemigrations --check --dry-run`.
- Team 17 tests on Launchpad; Orbit is for Team 21 and the course staff.
