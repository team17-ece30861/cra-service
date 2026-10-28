# Handoff: Quincy (Platform and Hosting)

**Last updated:** 2026-10-27 by Claude Code (Quincy's agent), after sending the Team 21 email.

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
- **Phase 4 is split by feature**, not rules-then-API. Richard: drafts, recording a
  submission, closing a ticket (rule, endpoint, and tests for each). Ann: the submission
  table, statuses, list filters and order, the privacy sweep, and the
  contract freeze. Table in [`docs/plan.md`](../plan.md#who-builds-what-in-phase-4).
- Quincy **isn't pursuing** the one-off 404 from Team 21's system (Oct 18) or the
  `registry-probe` 401s on our `/test/report` (Oct 20). The Phase 3 report said we'd share
  the 404's request sequence with Team 21 in Phase 4, so the Phase 4 report should say we
  dropped it and why.

## Alignment with Team 21 (as of 2026-10-27)

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

1. **Team 21 email: sent 2026-10-27** to Ryan Becker, cc Aashik, Andrew, Conrad. It asks:
   their tester to send our token and run against Orbit; approval of Ann's freeze PR
   (coming); a check of `pod-k-shared` PR #8; their Phase 4 endpoints and tests timeline
   (we launch Orbit Fri 10-30, cross-team run Sat 10-31); and answers to 10 questions by
   **noon Thu 10-29**, or we go ahead with our proposals. Email items are numbered 1 to 13:
   items 4 to 13 are plan Q1 to Q10 (item N = Q(N-3)), so "7: agree" means Q4. Items 10
   and 12 (Q7, Q9) change the contract, so they wait for Team 21's approval. Watch for
   replies and log answers in `docs/decisions.md`.
2. **Wed 10-28 morning, 4.U0: design standards** in `docs/design.md`, referenced from
   `CLAUDE.md`. Afternoon, **4.U1: Django sign-in** (decided 2026-10-27): built-in
   accounts, one per person, username sent as `X-Actor`. Also pick a name for the console
   (offer two or three options).
3. **Thu 10-29, 4.U2:** console pages on the existing endpoints: ticket list (state, report statuses,
   time until the next deadline), single ticket with audit trail, submit, triage.
   Server-rendered in the same Django service; the API token stays on the server; reporter
   details only on the single-ticket page.
4. **4.U3:** report pages (drafts with missing fields, record a submission, close) once
   Richard's 4.A2 to A4 are live. **4.U4:** UX notes and screenshots for the report.
5. **4.P1:** review Ann's and Richard's Phase 4 PRs as they arrive. **4.P2:** launch Orbit
   once 4.A2 to A5 pass on Launchpad (Fri 10-30), then merge the `pod-k-shared` update.
6. **4.A6: Schemathesis** (Quincy took it on 2026-10-26): at least 500 generated malformed
   requests against `openapi.yaml`, no 5xx, every error problem+json, data unchanged
   afterward. Runs in CI against the local service and from `acceptance/` against a
   deployment. Run it once Thursday's endpoints are merged: locally Friday, Launchpad
   Saturday. Covers AC-13.
7. 4.P4 (5xx alert) and 4.P5 (early performance check) if time allows. Both were promised
   in the Phase 3 report.

## Waiting on

- **Team 21:** replies to the 2026-10-27 email, plus their Phase 4 endpoints for the
  cross-team run on Sat 10-31.
- **Ann:** the submission model's fields today and 4.A1 merged Tuesday (review the
  migration the same day); statuses, filters, and order by Thursday; the freeze PR (3.9);
  accepting the `pod-k-shared` invite (`zuo30`, still pending on 2026-10-26).
- **Richard:** drafts merged Wednesday; submission and close by Thursday.

## Notes for the next session

- Claude Code's safety check merges a code PR only after Quincy names it in their own message
  ("merge #7"). Docs-only PRs can be merged by the agent.
- Team 17 never runs suites against Orbit; use Launchpad.
- Team 21 committed their tester straight to `pod-k-shared` `main`, including
  `__pycache__` files. It's harmless; mention it to them only if it comes up.
