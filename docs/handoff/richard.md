# Handoff: Richard (Domain Logic and Testing)

**Last updated:** 2026-11-22 by Quincy's agent (Claude Code), applying the review fixes
on Richard's two Phase 5 PRs. Richard's last session was 2026-11-20 (Codex).

## Where things stand

Phase 4 is delivered. Both Phase 5 test PRs are published, with CI passing on Richard's
own heads; review fixes were applied by Quincy's agent on 2026-11-22. Quincy approved
Team 17's agent resolving and merging them: #106 first, then #107.

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

## In progress

Nothing half-done on either branch. The two PRs wait on CI for the new heads, an
independent review, and the merge.

## Next up

1. After #106 merges: publish a commit-pinned design mapping and set
   `TESTER_MODEL_MAPPING_URL` (it stays empty until then, so own model counts are null
   with a reason). Confirm `TESTER_OWN_SYSTEM_URLS` with Quincy.
2. After both merge: check them on Launchpad (with Quincy's go), then refresh the
   `pod-k-shared` tester copy in the pod PR for Quincy's Orbit launch.
3. 5.10 still open: the two operation-table fixes from PR #83, the shared fixtures with
   Team 21 (4.T2), and the pod's multiple-problem 422 decision.
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
