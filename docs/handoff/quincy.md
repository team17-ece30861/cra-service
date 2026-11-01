# Handoff: Quincy (Platform and Hosting)

**Last updated:** 2026-11-01 by Claude Code (Quincy's agent), after the console design review (4.U0).

## Where things stand

Phase 4 is due **Sunday 2026-11-01 at midnight**. Every Phase 4 operation is on `main`
and Launchpad: drafts, recording a submission, closing, statuses in ticket responses,
list filters and order, the Q6 no-change rule, and the AC-16 privacy sweep (PRs #77 to
#88, each with an agent review posted on the PR). Full suite: 1219 passed against local Postgres on `main`.
**Orbit still runs Phase 3** (`262fedf`), so Team 21's tester gets 404 on the Phase 4
operations. Task status is in [`docs/plan.md`](../plan.md); Team 21's answers are in
[`docs/decisions.md`](../decisions.md) (2026-11-01).

**Console:** design standards are done ([`docs/design.md`](../design.md), 4.U0), with every
screen prototyped in `docs/design/ledger-screens.html` and approved by Quincy. No console
pages exist yet (4.U1 to U4).

Team 21's tester now authenticates on Orbit: first full run 2026-11-01 01:51 to 01:58 UTC
(client `team21`).

## In progress

- **pod-k-shared Phase 4 update** (branch `team17/phase4-release`): status chart,
  `team17/TESTING.md`, tester copy (222 tests). Open it after the Launchpad run; merge
  right after the Orbit launch.
- **pod-k-shared #14:** contract freeze (`0.2.0`, `phase-3` frozen, agreed Q answers as
  wording). Needs Team 21's approval; agents never merge it. After it merges, mirror
  `openapi.yaml` into this repo (needs a human teammate's approval here).
- **pod-k-shared #8:** shared test file E1 to E8, up to date with `main`. Team 21 checked
  it by email; it needs their approval on GitHub, then a human merges it.

## Next up

1. Run `acceptance/` against Launchpad (asks first: it resets Launchpad), including
   #81's oversized-body 401 cases, which may abort the connection on the real stack.
2. 4.P2: Quincy launches Orbit from `main`.
3. Open and then merge the `pod-k-shared` Phase 4 update (see In progress).
4. 4.A6 Schemathesis, if time allows.
5. Phase 4 report (`docs/reports/phase4.md`), using #83's operation table from a
   Launchpad or Orbit run, and noting that the cross-team run went one way.
6. Console pages: 4.U1 sign-in (auth, so guide it with Quincy), then 4.U2 and 4.U3, built
   to `docs/design.md`. 4.U4 (UX notes and screenshots for the report) can use the prototype.

## Waiting on

- **Team 21:** approve `pod-k-shared` #14 and #8; answer Q8; Phase 4 endpoint status.
- **Quincy:** the Orbit launch.

## Notes for the next session

- Merging a stacked PR with `--delete-branch` from the CLI closes the next PR instead of
  retargeting it. Retarget the next PR to `main` first, then merge, then delete.
- Two local pytest runs at once share the `test_team17` database and fail each other.
- Team 17 never runs suites against Orbit; use Launchpad.
- Claude Code merges a code PR only after Quincy says to in their own message.
