# Handoff: Quincy (Platform and Hosting)

**Last updated:** 2026-11-01 by Claude Code (Quincy's agent), at the end of Phase 4.

## Where things stand

Phase 4 is delivered and released. Orbit runs `de7a056` (launched 2026-11-01 21:47 UTC):
every Phase 3 and Phase 4 operation, the console, and the deployed tester with a 30-minute
run limit. Our tester passed 222/222 against Orbit; cross-team runs passed both ways on
2026-11-01 (ours 222/222 against Team 21's new deployment, theirs 17/17 against Orbit),
recorded in `pod-k-shared` (#17). The Phase 4 report text is in
[`docs/reports/phase4.md`](../reports/phase4.md). Task status is in
[`docs/plan.md`](../plan.md); Phase 5 owners are in its Phase 5 table (split agreed
2026-11-01, see [`docs/decisions.md`](../decisions.md)).

## In progress

- **`pod-k-shared` #14:** contract freeze (`0.2.0`), waiting on Team 21's approval. Once it
  merges, Ann mirrors `openapi.yaml` into this repo (5.9).

## Next up (Phase 5, Quincy's tasks)

1. 5.8 first: the early performance check, then 5.1 (AC-18 on Orbit) with Richard's load
   script.
2. 5.8: the 5xx alert; refuse a second deployed-tester run while one is going, and return
   before a long run ends; the console sign-in lockout (LIM-12).
3. 5.7: console without page reloads. 5.2: the restart demo.

## Waiting on

- **Team 21:** approve `pod-k-shared` #14; answer Q8.

## Notes for the next session

- Infrastructure is documented in [`docs/platform.md`](../platform.md), including the
  deployed tester, console accounts, container images, and what to delete at the end of
  the course. Disabled secret versions are still billed; destroy old versions.
- Merging a stacked PR with `--delete-branch` from the CLI closes the next PR instead of
  retargeting it. Retarget the next PR to `main` first, then merge, then delete.
- Two local pytest runs at once share the `test_team17` database and fail each other.
- A deployed-tester run takes about 12 minutes; some networks drop a connection that has
  been silent that long, so fetch the report with `GET /tester/test/report` afterwards.
- Team 17 tests on Launchpad; it ran against Orbit once after the Phase 4 release, for the
  report, with Quincy's go-ahead.
- Claude Code merges a code PR only after Quincy says to in their own message.
