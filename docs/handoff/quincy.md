# Handoff: Quincy (Platform and Hosting)

**Last updated:** 2026-10-26 by Claude Code (Quincy's agent), after the Phase 4 kickoff.

## Where things stand

Phase 4 is due **Sunday 2026-11-01**. The report questions aren't out yet. Phase 3 is done:
the ticket API and the course testing interface (`/test/setup`, `/test/report`, `/tester`)
are live on Launchpad and Orbit (`262fedf`). No Phase 4 code exists yet. The agreed
day-by-day schedule is in [`docs/plan.md`](../plan.md#proposed-schedule) (Quincy approved it
on 2026-10-26: "earlier is better for this team").

Decided at the kickoff (2026-10-26):

- Quincy builds a **console** (4.U1 to U4, see `docs/decisions.md`). Ann and Richard stay
  on the API and domain work. The console is cut first if that work slips.
- **Quincy sends the Team 21 email** (as PM), not Ann.
- **Schemathesis (4.A6) is offered to Richard** to lighten Ann's load. Not accepted yet.
- Quincy **isn't pursuing** the one-off 404 from Team 21's system (Oct 18) or the
  `registry-probe` 401s on our `/test/report` (Oct 20). The Phase 3 report said we'd share
  the 404's request sequence with Team 21 in Phase 4, so the Phase 4 report should say we
  dropped it and why.

## Alignment with Team 21 (as of 2026-10-26)

- **Testing has only gone one way.** Our tester passed 55/55 against them on 2026-10-18
  (Eastern). Their tester has never got past our token check: three 401s on 2026-10-19
  (UTC) because it didn't send the token we issued them. Orbit's logs show no successful
  request from them since. Their tester code has been in `pod-k-shared/team21/` since
  2026-10-19.
- **Contract still `0.1.0-draft`.** The Phase 3 freeze (3.9, Ann) never happened, and
  nothing is agreed for Phase 4 operations.
- **Shared test file unchecked:** `pod-k-shared` PR #8, open since 2026-10-18.
- **Testing-interface mismatch:** Team 21's `/test/setup` requires `X-Actor`; ours doesn't
  (plan open question Q10).
- **Open questions Q1 to Q10 all unanswered** (`docs/plan.md`). Q3, Q4, Q6, and Q9 matter
  most for Phase 4 tests.

## Next up

1. **Send the Team 21 email (today).** To Ryan Becker, cc the rest of Team 21 (Aashik,
   Andrew, Conrad). Then send the Ann and Richard messages (below). Draft:

   > Subject: Phase 4 kickoff: testing us, contract freeze, shared tests, spec questions
   >
   > Hi all, with Phase 4 due Sunday, here's what we'd like to settle early in the week:
   >
   > 1. **Run your tester against our Orbit deployment.** Your runs on Oct 18 got 401
   >    because the tester wasn't sending the token we sent you. Add it as a bearer
   >    token and run whenever you like, then send us the results. Testing has only
   >    gone one way so far.
   > 2. **Freeze the Phase 3 operations** in `pod-k-shared/openapi.yaml`. Ann will open a
   >    PR that bumps the version; it needs one approval from your team.
   > 3. **Shared test file (pod-k-shared PR #8):** Model D examples E1 to E8 with a
   >    runner. Could someone check the expected values and approve?
   > 4. **Spec questions.** We'd like answers by **Wednesday**. For anything still open
   >    then, we'll build our proposal and note it in the report.
   >    - Q1: triage of `invalid`/`not_actively_exploited` that includes `aware_at`. We
   >      accept it and ignore the time.
   >    - Q2: list order on equal or null `next_due_at`. Proposal: `received_at`
   >      ascending, then `id`.
   >    - Q3: drafts for a ticket that never became reportable. Proposal: 409. A ticket
   >      closed as `resolved` keeps returning its locked reports.
   >    - Q4: after a report is submitted, can changing `aware_at` or `fix.available_at`
   >      move its due time and flip it to `submitted_late`? What do you think?
   >    - Q5: must `submitted_at` be no earlier than the previous report's? Proposal: no
   >      extra rule.
   >    - Q6: a PATCH that changes nothing. Proposal: still one `updated` audit entry,
   >      with an empty `changes` list.
   >    - Q7: `POST /tickets` with a future `fix.available_at`. Proposal: add a 422.
   >    - Q8: the CRA starts the final-report clock at a corrective *or mitigating*
   >      measure. Proposal: define `fix.available_at` as the first of either (wording
   >      change only).
   >    - Q9: the early warning requires `member_states` and `affected_versions`, which
   >      the CRA asks for only "where applicable". Keep it strict, or allow "unknown"?
   >    - Q10: your `/test/setup` requires `X-Actor`; ours doesn't, and the course
   >      interface doesn't mention it. Proposal: not required. Our tester sends it
   >      either way.
   >
   > Thanks! Team 17

   Messages for Ann and Richard: point each at `docs/plan.md` (proposed schedule) and
   their own handoff file. Ask Richard for the 4.D1 to D5 signatures today and whether
   they'll take 4.A6. Tell Ann the 4.A1 to A5 target is Thursday.
2. **4.U1: decide how people sign in to the console** and how that becomes `X-Actor`.
   It's a guided decision because it touches auth. Options in `docs/plan.md`: per-person
   Django accounts, a shared password plus a name prompt, or Google sign-in in front of
   Cloud Run. Also pick a name for the console (offer two or three options).
3. **4.U2:** console pages on the existing endpoints: ticket list (state, report statuses,
   time until the next deadline), single ticket with audit trail, submit, triage.
   Server-rendered in the same Django service; the API token stays on the server; reporter
   details only on the single-ticket page.
4. **4.U3:** report pages (drafts with missing fields, record a submission, close) once
   Ann's 4.A2 to A4 are live. **4.U4:** UX notes and screenshots for the report.
5. **4.P1:** review Ann's and Richard's Phase 4 PRs as they arrive. **4.P2:** launch Orbit
   once 4.A2 to A5 pass on Launchpad (Fri 10-30), then merge the `pod-k-shared` update.
6. 4.P4 (5xx alert) and 4.P5 (early performance check) if time allows. Both were promised
   in the Phase 3 report.

## Waiting on

- **Team 21:** everything in the email above, plus their Phase 4 endpoints for the
  cross-team run on Sat 10-31.
- **Ann:** 4.A1 to A5 by Thursday, the freeze PR (3.9), and accepting the `pod-k-shared`
  invite (`zuo30`, still pending on 2026-10-26).
- **Richard:** 4.D1 to D5 signatures today, merged by Wednesday; an answer on 4.A6.

## Notes for the next session

- Claude Code's safety check merges a code PR only after Quincy names it in their own message
  ("merge #7"). Docs-only PRs can be merged by the agent.
- Team 17 never runs suites against Orbit; use Launchpad.
- Team 21 committed their tester straight to `pod-k-shared` `main`, including
  `__pycache__` files. It's harmless; mention it to them only if it comes up.
