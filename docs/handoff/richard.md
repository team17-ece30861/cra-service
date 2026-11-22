# Handoff: Richard (Domain Logic and Testing)

**Last updated:** 2026-11-22 by Quincy's agent (Claude Code), applying the review fixes
on Richard's three Phase 5 PRs. Richard's last session was 2026-11-21 (Codex).

## Where things stand

Phase 4 is delivered. All three Phase 5 test PRs are published, with CI passing on
Richard's own heads; review fixes were applied by Quincy's agent on 2026-11-22. Quincy
approved on 2026-11-21 that Team 17's agent resolves and merges Richard's PRs, with
Quincy's go for each merge. Order: #106, then #107, then #108. Each later branch has the
earlier ones merged in, so use merge commits, not squash.

- **[PR #106](https://github.com/team17-ece30861/cra-service/pull/106)** (5.4,
  `codex/phase5-model-coverage`): own-system `coverage.model` from the approved
  44-requirement design ([model-coverage.md](../model-coverage.md)). CI passed 1,494
  tests at `81a05eb`. Review fixes: failed oracle groups now name each failed
  comparison in the report message (`OracleChecks`), an own-system example report in
  `docs/interface/tester.yaml`, and the "unexpected 5xx = not evaluated" rule in
  model-coverage.md.
- **[PR #107](https://github.com/team17-ece30861/cra-service/pull/107)** (5.10,
  `codex/phase5-http-gaps`): 19 portable cases for AC-07, PATCH/triage 404 and 413,
  and `DELETE /test/clock`. CI passed 1,424 tests at `5c616b7`. Review fixes: the AC-07
  audit check no longer asserts nested field naming or the change count, a missing
  `change_reason` may name `change_reason` or `aware_at`, and clock release compares
  parsed times with 1 s slack. #106 is merged into this branch, so it holds both.
- **[PR #108](https://github.com/team17-ece30861/cra-service/pull/108)** (5.10,
  `codex/phase5-operation-reporting`): the two operation-table fixes from PR #83's
  review. Failed setup checks stay in the report, and early-stopped, filtered or
  interrupted runs say `incomplete` with counts and reasons. CI passed 1,417 tests at
  `c490982`. Review fixes: a check that got no response (connection failure, timeout)
  is inconclusive rather than failed, and a run from a parent directory says the
  selection is broader than the suite. #107 (with #106) is merged into this branch.

## In progress

Nothing half-done on any of the three branches. They wait on CI for the new heads, an
independent review, and the merges.

## Next up

1. After #106 merges: publish a commit-pinned design mapping and set
   `TESTER_MODEL_MAPPING_URL` (it stays empty until then, so own model counts are null
   with a reason). Confirm `TESTER_OWN_SYSTEM_URLS` with Quincy.
2. After all three merge: check them on Launchpad (with Quincy's go), then refresh the
   `pod-k-shared` tester copy (including the new `acceptance/observations.py`) in the
   pod PR for Quincy's Orbit launch.
3. 5.10 still open: the shared fixtures with Team 21 (4.T2) and the pod's
   multiple-problem 422 decision.
4. 5.1: agree the load protocol before writing the script. 5.4/5.6: full and
   cross-team results before submission.

## Waiting on

Quincy: mapping URL, own-system URLs, Launchpad check and Orbit launch. Ann and
Team 21: contract decisions and shared fixtures.

## Notes for the next session

- Model coverage counts evaluated design scenarios, not passes: don't present 19/44
  as 19 delivered or passing requirements.
- The clock-release case compares against the runner's wall clock with 120 s skew;
  keep the runner and target clocks in sync.
- New HTTP-gap cases have no model bindings yet; add them only with a design-version
  update.
