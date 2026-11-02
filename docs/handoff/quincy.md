# Handoff: Quincy (Platform and Hosting)

**Last updated:** 2026-11-02 by Claude Code (Quincy's agent).

## Where things stand

Phase 4 is delivered and released. Orbit runs `de7a056` (launched 2026-11-01 21:47 UTC):
every Phase 3 and Phase 4 operation, the console, and the deployed tester with a 30-minute
run limit. Our tester passed 222/222 against Orbit; cross-team runs passed both ways on
2026-11-01 (ours 222/222 against Team 21's new deployment, theirs 17/17 against Orbit),
recorded in `pod-k-shared` (#17). The Phase 4 report text is in
[`docs/reports/phase4.md`](../reports/phase4.md). Task status is in
[`docs/plan.md`](../plan.md); Phase 5 owners are in its Phase 5 table (split agreed
2026-11-01, see [`docs/decisions.md`](../decisions.md)).

On 2026-11-02 we checked the service against the course's "Cross-team Testing Interface"
document and closed its gaps (5.11): an aborted tester run keeps its results (#103), every
interface error carries `message` and `source` (#103), and OpenAPI descriptions of the
tester and the system's test endpoints are in [`docs/interface/`](../interface/) (#104).
Both are on Launchpad (`2768aa2`, checked 2026-11-02), not yet on Orbit.

## In progress

- **Next Orbit launch** picks up #103 and #104. Right after it, set the version row in
  `team17/SYSTEM.md` on `pod-k-shared` #19 (draft) to the launched commit and merge #19.
- **`pod-k-shared` #14:** contract freeze (`0.2.0`), waiting on Team 21's approval. Once it
  merges, Ann mirrors `openapi.yaml` into this repo (5.9).

## Next up (Phase 5, Quincy's tasks)

1. 5.8 first: the early performance check, then 5.1 (AC-18 on Orbit) with Richard's load
   script.
2. 5.8: the 5xx alert; refuse a second deployed-tester run while one is going, and return
   before a long run ends; recover a tester session stuck in `running` after a restart;
   the console sign-in lockout (LIM-12); LIM-13 (tester cleans up after a run).
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
- A deployed-tester run takes about 11 to 12 minutes; some networks drop a connection that
  has been silent that long (ours dropped at 540 s), so fetch the report with
  `GET /tester/test/report` afterwards. The run carries on without the client.
- `docs/interface/*.yaml` are checked against real responses by
  `tests/test_interface_descriptions.py`: change them together with any tester or
  `/test/setup`/`/test/report` behavior, and refresh the copies in `pod-k-shared/team17/`.
- Team 17 tests on Launchpad; it ran against Orbit once after the Phase 4 release, for the
  report, with Quincy's go-ahead.
- Claude Code merges a code PR only after Quincy says to in their own message.
