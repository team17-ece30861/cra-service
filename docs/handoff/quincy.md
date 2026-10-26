# Handoff: Quincy (Platform and Hosting)

**Last updated:** 2026-10-26 by Claude Code (Quincy's agent).

## Where things stand

Phase 4 is due **Sunday 2026-11-01**. The report questions aren't out yet. Phase 3 is done:
the ticket API and the course testing interface (`/test/setup`, `/test/report`, `/tester`)
are live on Launchpad and Orbit (`262fedf`). No Phase 4 code exists yet. The proposed
day-by-day schedule is in [`docs/plan.md`](../plan.md#proposed-schedule).

On 2026-10-26 Quincy moved our own intake channel up from Phase 5 as a console for a
manufacturer's security team (tasks 4.U1 to U4, see `docs/decisions.md`). Quincy builds
it; Ann and Richard stay on the API and domain work.

## In progress

- Branch `docs/phase4-kickoff`: this plan refresh, the decision entry, and this file.
- Kickoff drafts given in chat on 2026-10-26, not yet sent: an email to Team 21, and
  messages to Ann and Richard.

## Next up

1. **4.U1:** decide how people sign in to the console and how that becomes `X-Actor`.
   It's a guided decision because it touches auth.
2. **4.U2:** console pages on the existing endpoints.
3. **4.P1:** review Ann's and Richard's Phase 4 PRs as they arrive.
4. **4.P2:** launch Orbit once 4.A2 to A5 pass on Launchpad (proposed Fri 10-30), then
   merge the `pod-k-shared` update.
5. 4.P4 (5xx alert) and 4.P5 (early performance check) if time allows. Both were promised
   in the Phase 3 report.

## Waiting on

- **Team 21:** the contract freeze (3.9), their check of `pod-k-shared` PR #8 (open since
  2026-10-18), answers to Q2 to Q9, running their tester against Orbit, and their Phase 4
  endpoints for the cross-team run.
- **Ann:** 4.A1 to A8. Ann's handoff file still has the 2026-10-18 version.
- **Richard:** function signatures for 4.D1 to D5, then the rules and 4.T1. Richard's
  handoff file still has the 2026-10-18 version.

## Notes for the next session

- Claude Code's safety check merges a code PR only after Quincy names it in their own message
  ("merge #7"). Docs-only PRs can be merged by the agent.
- Team 17 never runs suites against Orbit; use Launchpad.
- Team 21 committed their tester straight to `pod-k-shared` `main` on 2026-10-19,
  including `__pycache__` files. It's harmless, but worth a gentle note to them.
