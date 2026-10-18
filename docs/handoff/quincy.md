# Handoff: Quincy (Platform and Hosting)

**Last updated:** 2026-10-18 by Claude Code (Quincy's agent).

## Where things stand

Phase 3 is due **2026-10-18**. The Phase 3 code is merged (PR #7, `6548e49`) and live on
both deployments: Launchpad and Orbit (`262fedf`, launched by Quincy at 00:45 UTC). The
acceptance suite passed 55/55 on each. Orbit was then reset and returned to real time
(00:55 UTC). The shared pod repo `team17-ece30861/pod-k-shared` exists (private) with our
base URL, the pod rules, and a status chart (operations and milestones by team) in its
README.

## In progress

- No open branches in `cra-service`.
- `pod-k-shared` invites are pending for `richardlin-btfu`, `zuo30`, and `Becker42`. Only
  one Team 21 member is invited so far.

## Next up

1. **Task 3.7:** find out what the "class registry entry" is (likely on the course site)
   and add it. Team 21's token was sent through OneDrive on 2026-10-18 (marked Done in
   the `pod-k-shared` status chart). Delete the OneDrive file once Team 21 confirms they
   saved it. The staff token (`prod-api-token-staff`) goes to the course staff the same
   way when they review.
2. Decide whether to invite the rest of Team 21 (Aashik, Andrew, Conrad) to `pod-k-shared`,
   or leave that to Ryan.
3. **Task 3.11:** the Phase 3 report. Q7 and Q8 still describe FastAPI and SQLite; the
   evidence for the rewrite is in `docs/phase3.md` and `docs/decisions.md`.
4. Phase 4 platform tasks 4.P1 to 4.P3.

## Waiting on

- **Ann:** the contract freeze with Team 21 (3.9, deadline-critical) and Ann's review of the
  merged code (3.1). Ann's handoff is in `ann.md`.
- **Richard:** cross-team runs (3.8) and the shared test file (3.10).
- **Team 21:** confirming they saved the token, their base URL in `pod-k-shared`, a token
  for us, and accepting the invite.

## Notes for the next session

- Class registry (Google Sheet) values are ready, in chat on 2026-10-18: system URL, tester
  link (`pod-k-shared/team17/tester`), spec link, and access notes. The registry entry's
  date goes into report Q2.2.

- Claude Code's safety check merges a code PR only after Quincy names it in their own message
  ("merge #7"). Docs-only PRs can be merged by the agent.
- Team 17 never runs suites against Orbit; use Launchpad.
- Launchpad's test clock is still frozen from the 22:04 UTC run.
- The Field Guide page (https://claude.ai/artifact/GjzNLxnmFqXwJhzm2tu1x5) is private
  until Quincy shares it, and its Phase 3 table is a snapshot from the evening of
  2026-10-17.
