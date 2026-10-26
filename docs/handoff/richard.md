# Handoff: Richard (Domain Logic and Testing)

**Last updated:** 2026-10-26 by Quincy's agent (Claude Code), from the Phase 4 kickoff with
Quincy. Richard's agent: rewrite this file in your own words at the end of your next session.

**For Richard's agent:** you're working for Richard, who owns Domain Logic and Testing on
Team 17. Read [`AGENTS.md`](../../AGENTS.md) and [`docs/plan.md`](../plan.md) before starting.

## Where things stand

Phase 4 is due **Sunday 2026-11-01**. Phase 3 is done and live on both deployments
(55/55). None of the Phase 4 code exists yet.

**Phase 4 is split by feature** (Quincy, 2026-10-26): each person writes the rule in
`core/domain/`, the endpoint, and the tests for their own features. Richard builds the
reports end to end: **drafts, recording a submission, and closing a ticket**. Ann has the
submission table, statuses, list filters, the privacy sweep, and the
contract freeze; Quincy has Schemathesis. See [Who builds what in Phase 4](../plan.md#who-builds-what-in-phase-4)
and the day-by-day [schedule](../plan.md#proposed-schedule). Richard built the Phase 3 API
(PR #7), so this is familiar ground. Quincy is building a web console on top of the API
and reviews every PR.

## Next up

1. **Drafts (4.D1 rule, 4.A2 endpoint; start Mon, merged Wed 10-28):** for each report
   type, build `content` and `missing_fields` exactly as Model C says, never including
   reporter fields. Unit tests fill fields one at a time and check all four drafts at each
   step. `GET /tickets/{id}/reports/{type}`: unknown type → 404; before submission, build
   the draft live; after submission, return the locked snapshot.
2. **Recording a submission (4.D3 rule, 4.A3 endpoint; Wed to Thu):** 409 if the ticket
   isn't `reportable`, the previous report isn't submitted, or this one already is; 422 if
   required fields are missing or `submitted_at` isn't between `aware_at` and now (409
   before 422). `user_advisory` and unknown types → 404. Store the snapshot in Ann's
   submission table (4.A1, merged Tue; Ann posts its fields Monday), add one
   `report_submitted` audit entry, and return the locked report.
3. **Closing a ticket (4.D4 rule, 4.A4 endpoint; Thu):** 409 unless `reportable` with all
   three reports submitted; set `closed`/`resolved`; add one `closed` audit entry.
4. **Acceptance cases for these features (Thu):** AC-08, 09, 10, and 12 in
   `acceptance/cases.py`. Ann adds hers (AC-06, 11, 16). Richard keeps the harness.
   **Target: everything above merged by Thu 10-29.**
5. **Fri 10-30:** run `acceptance/` against Launchpad; fix or report failures.
6. **4.T4 (Sat 10-31): cross-team run, both directions**, after Quincy launches Orbit.
   Classify each mismatch as our bug, their bug, or a spec gap.
7. If time allows: 4.T2 (Phase 4 cases in the shared test file), 4.T5 (status table from
   the runner), 4.T6 (audit 404/405 tests).

## Alignment with Team 21 (as of 2026-10-26)

- **Testing has only gone one way.** Our tester passed 55/55 against Team 21 on 2026-10-18
  (Eastern). Their tester has never got past our token check (401s, because it didn't
  send the token we issued). Quincy's email (being sent 2026-10-26) asks them to fix that
  and run against Orbit.
- **Shared test file:** `pod-k-shared` PR #8 (E1 to E8 plus runner) is still waiting on
  Team 21's check. Fill in `checked_by` once they approve.
- **Testing-interface mismatch (Q10):** Team 21's `/test/setup` requires `X-Actor`; ours
  doesn't. Our tester sends it anyway (PR #64), so this doesn't block our runs.
- **Open questions Q1 to Q10** (`docs/plan.md`) are going to Team 21 in Quincy's email
  (2026-10-26), with a Wed 10-28 deadline. Q3 (drafts for never-reportable tickets), Q5
  (submission order of `submitted_at`), and Q9 (early-warning required fields) change
  Richard's features. If one is still open when you build, use the plan's proposal and
  note it in the PR.
- Quincy isn't pursuing the one-off 404 seen in Team 21's system on 2026-10-18.

## Waiting on

- **Ann:** the submission model's fields (Mon) and 4.A1 merged (Tue).
- **Team 21:** answers to Q1 to Q10, the PR #8 check, and their Phase 4 endpoints by Sat.

## Notes for the next session

- Ann edits `core/tickets.py` too. Keep PRs small and merge often to limit conflicts.
- **Where to test:** Team 17 runs suites against **Launchpad** only. Orbit is for Team 21
  and the course staff. Running against Team 21's deployment is fine for cross-team runs.
- Launchpad's token is in Secret Manager as `dev-api-token`. Ask Quincy; never paste it
  into a prompt or a commit.
- Expected values in tests come from `docs/spec.md` or hand calculation, never from the
  code under test.
