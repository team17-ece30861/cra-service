# Handoff: Richard (Domain Logic and Testing)

**Last updated:** 2026-10-18 by Quincy's agent (Claude Code), from the merged PRs and the
plan. Richard's agent: rewrite this file in your own words at the end of your next session.

**For Richard's agent:** you're working for Richard, who owns Domain Logic and Testing on
Team 17. Read [`AGENTS.md`](../../AGENTS.md) and [`docs/plan.md`](../plan.md) before starting.

## Where things stand

Phase 3 is due **2026-10-18**. PRs #5, #6, and #7 are merged. Quincy's agent ran Richard's
acceptance suite against both deployments on 2026-10-18 (tasks 3.5 and 3.6), with 55/55
passing on each; results are in `docs/phase3.md`. It also added PATCH regression tests to
`tests/test_phase3_api.py` (PR #11).

## Next up

1. **Task 3.8: cross-team runs with Team 21.** Run our suite against Team 21's deployment,
   and make sure Team 21 runs theirs against Orbit. Classify every mismatch as our bug,
   their bug, or a gap in the spec. Blocked until Team 21 adds their base URL to
   `pod-k-shared` and sends a token (Quincy relays it privately).
2. **Task 3.10: the shared test file.** Quincy's agent finished it on 2026-10-18:
   `pod-k-shared` PR #8 adds `tests/model-d.json` (E1 to E8 as runnable steps) and
   `tests/run.py`. It's waiting on Team 21's check. Follow up with them, and fill in
   `checked_by` once they approve. Phase 4 cases go in the same format.
3. **Task 4.T3: harness README.** Running needs `CRA_BASE_URL`, `CRA_API_TOKEN`, and
   `--allow-reset`.
4. **Phase 4 domain work (4.D1 to 4.D5):** drafts per Model C, submitted statuses,
   submission and close rules, listing helpers. Agree on function signatures with Ann in
   the first PR.

## Waiting on

- **Team 21:** their base URL in `pod-k-shared` and a token for us (needed for 3.8).
- **Richard:** accept the invite to `team17-ece30861/pod-k-shared`.

## Notes for the next session

- **Where to test:** Team 17 runs suites against **Launchpad** only. Orbit is for Team 21
  and the course staff (rule in `pod-k-shared`'s README). Running against Team 21's
  deployment is fine for 3.8.
- Launchpad's token is in Secret Manager as `dev-api-token`. Ask Quincy; never paste it
  into a prompt or a commit.
- The Launchpad run on 2026-10-18 left its test clock frozen. Run `DELETE /test/clock` if
  you need real time there.
- Expected values in tests come from `docs/spec.md` or hand calculation, never from the
  code under test.
