# Handoff: Quincy (Platform and Hosting)

**Last updated:** 2026-11-22 by Claude Code (Quincy's agent).

## Where things stand

Phase 5 is released. Orbit runs `c875f14` (launched 2026-11-22 17:12 UTC; revision
`team17-prod-00012-wnv` since the AC-19 restart demo), with every Phase 5 PR (#106 to
#119). Results on Orbit that day, all recorded in [`docs/system.md`](../system.md):
- our deployed tester: 241 of 241
- AC-18: p95 736 ms with 1,000 tickets
- AC-13: 683 malformed requests, 0 server errors, data unchanged
- Team 21's published tester: 17 of 17
- AC-19: recorded by Quincy (video linked in the Phase 5 report)
- our suite against Team 21's deployment: 233 of 241 (8 Team 21 deviations from agreed rules)

`pod-k-shared` #20 (contract 0.3.0), #19 (interface descriptions) and #21 (tester copy,
TESTING.md, SYSTEM.md, status chart) are merged. Task status is in
[`docs/plan.md`](../plan.md), decisions in [`docs/decisions.md`](../decisions.md).

Team 21 hasn't answered on GitHub or by email since 2026-11-01. Team 17 decided the open
pod items itself, and Quincy chose not to message them first (2026-11-22).

## In progress

- The Phase 5 report (`docs/reports/phase5.md`, and the Word document in the team's
  OneDrive): everything filled except each teammate's Q8.1.

## Next up

1. Submit the Phase 5 report once Q8.1 is in.
2. After grading: tear down the billable resources (`docs/platform.md`, "End of the course").

## Waiting on

- **Ann and Richard:** their own Q8.1 (GenAI use) paragraphs for the report.

## Notes for the next session

- Infrastructure is in [`docs/platform.md`](../platform.md); the on-call version is
  [`docs/operations.md`](../operations.md).
- The 5xx alert emails Quincy's Purdue address for both services; rerun
  `scripts/create_5xx_alert.sh EMAIL` to change it.
- Orbit's revision 00012 carries an `AC19_RESTART_MARKER` env var from the demo; the next
  launch drops it.
