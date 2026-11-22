# Handoff: Quincy (Platform and Hosting)

**Last updated:** 2026-11-22 by Claude Code (Quincy's agent).

## Where things stand

Phase 5 is due 2026-11-22 23:59 ET. Merged to `main` and on Launchpad (`256c3d9`):
own-system model coverage and the HTTP-gap and operation-table fixes (Richard's #106,
#107, #108), the console sign-in lockout (#109), contract 0.3.0 with Q7, Q8 and Q9 (#111),
the deployed tester's run rules, recovery and cleanup (#112), the pinned model-coverage
mapping URL (#114), console saves in place (#115), persistent database connections and
gzip (#116), and the AC-18 performance script (#110). On Launchpad after #116, a warm
simple read takes about 42 ms on the server, down from about 192 ms. Orbit still runs the
Phase 4 release. Task status is in [`docs/plan.md`](../plan.md), decisions in
[`docs/decisions.md`](../decisions.md).

Team 21 hasn't answered on GitHub or by email since 2026-11-01. Team 17 decided the open
pod items itself, and Quincy chose not to message them first (2026-11-22).

## In progress

- **Open PRs:** #113 (AC-13 Schemathesis, corpus pinned per operating system), #117 (Ann's
  operations guide, with follow-up fixes), #118 (AC-19 restart demo and 5xx alert
  scripts), and this docs PR.
- **Orbit launch** (Quincy: `gh workflow run orbit.yml --ref main -f confirm=ORBIT`), then
  right after it: merge `pod-k-shared` #20 (contract 0.3.0) and #19 (tester OpenAPI
  descriptions, with the launched commit in `team17/SYSTEM.md`), and a new pod PR that
  refreshes `team17/tester/`, `TESTING.md` (gzip, the tester's 409s, `coverage.model`),
  `SYSTEM.md` and the status chart.
- **Evidence for the report** (`docs/reports/phase5.md`): AC-18 on Orbit, AC-13 CLI run,
  deployed tester run at the launched commit, AC-19 screen recording on Orbit
  (`scripts/restart_demo.sh prod`, Quincy), our suite against Team 21 after 11 PM ET
  (resets their data; approved 2026-11-21), Team 21's published tester against Orbit, and a
  Cloud Logging excerpt.

## Next up

1. Merge #113, #117, #118 and this PR; launch Orbit; merge the pod PRs.
2. Collect the evidence above and finish the Phase 5 report (5.1, 5.2, 5.6).
3. After grading: tear down the billable resources (`docs/platform.md`, "End of the course").

## Waiting on

- **Quincy:** merge go for the open PRs, the Orbit launch, and the AC-19 recording.
- **Richard:** record the final cross-team results (5.6) from tonight's runs.

## Notes for the next session

- Infrastructure is in [`docs/platform.md`](../platform.md); the on-call version is
  [`docs/operations.md`](../operations.md) once #117 merges.
- The 5xx alert emails Quincy's Purdue address for both services; rerun
  `scripts/create_5xx_alert.sh EMAIL` to change it.
- The AC-13 corpus differs between Linux (664 requests) and macOS (683); CI checks only
  the Linux one. Run the CLI on a Mac to check the macOS pin.
- Don't deploy or launch Orbit while a deployed-tester run is going; it cuts the run off.
- Claude Code merges a code PR only after Quincy says to in their own message.
