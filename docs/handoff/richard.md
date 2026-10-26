# Handoff: Richard (Domain Logic and Testing)

**Last updated:** 2026-10-26 by Quincy's agent (Claude Code), from the Phase 4 kickoff with
Quincy. Richard's agent: rewrite this file in your own words at the end of your next session.

**For Richard's agent:** you're working for Richard, who owns Domain Logic and Testing on
Team 17. Read [`AGENTS.md`](../../AGENTS.md) and [`docs/plan.md`](../plan.md) before starting.

## Where things stand

Phase 4 is due **Sunday 2026-11-01**. Phase 3 is done and live on both deployments
(55/55). No Phase 4 code exists yet. Richard's rules come first, because Ann's endpoints
are built on them. The day-by-day schedule is in
[`docs/plan.md`](../plan.md#proposed-schedule).

At the kickoff, Quincy took on a web console on top of the API (4.U1 to U4), so Ann holds
all the Phase 4 API work. To balance that, **Schemathesis (4.A6) is offered to Richard**.
Tell Quincy yes or no.

## Next up

1. **Today (Mon 10-26): post the function signatures for 4.D1 to D5** in a PR description,
   so Ann can build against them in parallel.
2. **4.D1 to D5, merged by Wed 10-28:** drafts per Model C (never including reporter
   fields), `submitted`/`submitted_late` statuses, the submission rule (409 before 422),
   the close rule, and the listing helpers (`next_due_at` and sort order).
3. **4.T1 (Thu):** acceptance cases for AC-06 to 12 and AC-16 in `acceptance/cases.py`.
4. **Fri 10-30:** run `acceptance/` against Launchpad once Ann's endpoints are merged; fix
   or report failures.
5. **4.T4 (Sat 10-31): cross-team run, both directions**, after Quincy launches Orbit.
   Classify each mismatch as our bug, their bug, or a spec gap.
6. **4.A6, if accepted:** Schemathesis, at least 500 generated malformed requests, no 5xx,
   every error problem+json, data unchanged.
7. If time allows: 4.T2 (Phase 4 cases in the shared test file), 4.T5 (status table from
   the runner), 4.T6 (audit 404/405 tests).

## Alignment with Team 21 (as of 2026-10-26)

- **Testing has only gone one way.** Our tester passed 55/55 against Team 21 on 2026-10-18
  (Eastern). Their tester has never got past our token check (401s, because it didn't
  send the token we issued). Quincy's email (being sent 2026-10-26) asks them to fix that and run
  against Orbit.
- **Shared test file:** `pod-k-shared` PR #8 (E1 to E8 plus runner) is still waiting on
  Team 21's check. Fill in `checked_by` once they approve.
- **Testing-interface mismatch (Q10):** Team 21's `/test/setup` requires `X-Actor`; ours
  doesn't. Our tester sends it anyway (PR #64), so this doesn't block our runs.
- **Open questions Q1 to Q10** (`docs/plan.md`) are going to Team 21 in Quincy's email (2026-10-26), with a Wed 10-28
  deadline. Q2 (list tie-break), Q4 (whether a later date change can flip a submitted
  report to late), Q5, and Q9 (early-warning required fields) change Richard's rules. If
  one is still open when you build, use the plan's proposal and note it in the PR.
- Quincy isn't pursuing the one-off 404 seen in Team 21's system on 2026-10-18.

## Notes for the next session

- **Where to test:** Team 17 runs suites against **Launchpad** only. Orbit is for Team 21
  and the course staff. Running against Team 21's deployment is fine for cross-team runs.
- Launchpad's token is in Secret Manager as `dev-api-token`. Ask Quincy; never paste it
  into a prompt or a commit.
- Expected values in tests come from `docs/spec.md` or hand calculation, never from the
  code under test.
