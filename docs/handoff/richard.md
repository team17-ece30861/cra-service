# Handoff: Richard (Domain Logic and Testing)

**Last updated:** 2026-11-22 by Quincy's agent (Claude Code). Richard's last session was
2026-11-21 (Codex).

## Where things stand

All three of Richard's Phase 5 PRs are merged and on Launchpad: own-system model
coverage (#106), the HTTP-gap cases (#107), and the operation-table fixes (#108), each
with review fixes from Quincy's agent. The mapping URL is pinned in #114, so own-system
reports carry numeric `coverage.model` counts. Quincy's agent built the AC-18 load script
(#110).

## In progress

Nothing half-done.

## Next up

1. **5.6, results (handed over by Quincy's agent, 2026-11-22):** record the final
   cross-team results from tonight's runs: our suite against Team 21's deployment, and
   Team 21's published tester against Orbit. For each: date, both commits or versions,
   pass/fail counts, and each mismatch's classification.
2. 5.10 leftovers: the shared fixtures with Team 21 (4.T2). The pod's 422 question is
   settled (a 422 lists every problem, contract 0.3.0).

## Waiting on

Quincy: the Orbit launch and the cross-team runs. Team 21: shared fixtures.

## Notes for the next session

- Model coverage counts evaluated design scenarios, not passes: don't present the counts
  as delivered or passing requirements.
- The clock-release case compares against the runner's wall clock with 120 s skew;
  keep the runner and target clocks in sync.
- New HTTP-gap cases have no model bindings yet; add them only with a design-version
  update.
