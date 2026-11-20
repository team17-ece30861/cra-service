# Handoff: Richard (Domain Logic and Testing)

**Last updated:** 2026-11-20 by Codex with Richard.

## Where things stand

Phase 4 PRs #77-83 are merged; the team's handoffs record the November 1 release
and successful cross-team runs. Do not revive the old draft-PR blockers. Latest
fetched main is `ecb59a7` (November 2). No live release/registry check was performed
this session.

Richard approved the 44-requirement Phase 5 model-coverage baseline for local
implementation on November 19, then authorized a branch, commit, push, draft PR
and PostgreSQL CI on November 20. Merging, deployment and shared resets remain
separate actions. See
[model-coverage.md](../model-coverage.md) and the full Phase 5 owners in
[plan.md](../plan.md).

## In progress

- Implementation is prepared on `codex/phase5-model-coverage`, based on fetched
  main `ecb59a7`, in the reused `work/cra-publish-t5` checkout. Draft publication
  and current PostgreSQL CI are pending; original Phase 4 branches and the user's
  original checkout are preserved.
- Own-system `coverage.model` uses 44 fixed requirements, 266 scenarios and exact
  test bindings. 141 scenarios are bound; 125 stay unbound/incomplete. A reached
  failed oracle is evaluated, not passing conformance. CI/manual/name inference
  does not supply credit.
- Same-team identity uses exact configured full base URLs, not tokens/host guesses.
  `TESTER_MODEL_MAPPING_URL` intentionally defaults to empty: own model counts
  are null with a reason until the mapping is published/configured. Cross-team
  reports omit model. Quincy must confirm the own-system URL list before release.
- Journaling retains call-phase evaluations on abort and truncated final reports;
  invalid/version-mismatched evidence stays unavailable. Schema docs are updated
  to tester-description version 1.1.0; the pod project contract is unchanged.
- Final selected local regression passes **1,262 tests with four existing
  PostgreSQL-only skips**, including 89 new model tests. Ruff lint/format checks
  pass across 136 Python files; Django and migration checks pass. This is not
  current Linux/PostgreSQL CI or a full Windows-suite claim.
- The nested real-pytest/Django portable run passed 221 cases with one HTTPS probe
  skip, recorded 140 scenarios and evaluated 19/44 requirements. This is local
  in-process evidence with a synthetic mapping URL, not deployed HTTP evidence.
- Independent local review found status-comparison undercount, early compound
  predicate credit and pre-edit locking checks, plus a remaining short-circuit
  status/deadline case. Corrections and negative regression probes are present;
  final re-review reports no new actionable findings. The reviewer is closed.
  No posted independent PR approval is claimed.

## Next up

1. Publish the authorized model-coverage draft into main and inspect current CI.
   Code still needs posted independent review and passing Linux/PostgreSQL CI
   before any separately authorized merge. Quincy should review the nonsecret
   settings and interface changes in his platform area.
2. Coordinate with Quincy: confirm own-system bases, publish a version-pinned
   mapping URL, configure it, verify on Launchpad with explicit reset permission,
   and follow his Orbit/shared-copy release process.
3. 5.10: operation-table partial-run/setup-failure fixes; AC-07 and remaining
   PATCH/triage 404/413 and successful clock-release HTTP tests; shared fixtures
   and the pod's multiple-problem 422 decision. These are not completed by model
   instrumentation.
4. 5.1: agree the performance request mix, warm-up and measurement protocol before
   building the load script; Quincy owns the deployed stress run. 5.4/5.6: fresh
   full regression and both-direction cross-team evidence before submission.

## Waiting on

Published mapping/configuration and release coordination (Quincy); outstanding pod
decisions/contract work (Ann with Team 21); PostgreSQL CI and deployed verification.
The November 20 authorization covers this draft publication and CI, not merging,
remote reset tests, deployment, performance runs or restarts.

## Notes for the next session

Do not turn 19/44 model evaluations into 19 delivered features or 19 passing
requirements. Incomplete/CI-only scenarios remain in the denominator. Compound
oracle predicates are evaluated eagerly; snapshots are checked after edits for
all three report types. Status checkpoints preserve evaluable failures but do not
invent evaluations from transport failures or unexpected server errors.

No workflow, migration, database model, auth/token handling, pod project OpenAPI,
Ann/Quincy handoff or shared repository was changed. Existing Windows full-suite
blockers and the old localhost transport diagnosis were not bypassed or repaired.
These local results do not replace Linux/PostgreSQL CI or authorized real HTTP
acceptance.

Local evidence summary is in the parent chat workspace's
`outputs/phase5-model-coverage-local-2026-11-19.md` and `.json`; detailed parent
results are `work/phase5-model-regression-20261119-final.xml`. These local paths
are not public release evidence.
