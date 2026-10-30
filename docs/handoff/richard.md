# Handoff: Richard (Domain Logic and Testing)

**Last updated:** 2026-10-30 by Codex, after starting Phase 4 with Richard.

## Where things stand

The recorded Phase 4 deadline is Sunday 2026-11-01; confirm its exact time in
Gradescope. Main at this session's start is `79b8b4a` (PR #74), containing the
feature split and planning updates but no Phase 4 implementation.

Richard owns drafts, recording submissions, and closing tickets end to end under
the October 26 feature split. Ann owns the recorded-report table, statuses,
listing, confidentiality sweep, and contract freeze. Quincy owns Schemathesis,
review, releases, and the optional console.

## In progress

- **4.D1:** the pure `build_draft` generator and Model C tests are implemented in
  the current local change, with integration notes in `docs/domain.md`.
- All four report types use explicit field allowlists, dotted missing-field
  paths, deep-copied output, UTC seconds, and no reporter data.
- Local validation passed 300 domain/timestamp tests, including 181 new draft
  cases; Ruff lint and format checks passed for the new Python files.
- This work is prepared for PR review on `codex/phase4-draft-generator`, based
  on current main in an isolated checkout. The local generator review found no
  actionable issues; it is separate from the required PR review before merge.
  No merge, deployment, or remote acceptance/reset was performed.
- No draft HTTP route or recorded-report storage has been added. 4.A2, AC-08
  HTTP acceptance, and locked submitted-content reads remain pending.

## Next up

1. Complete CI and the required independent PR review for 4.D1. Merge only with
   Richard's separate go-ahead through the team's normal process.
2. Confirm Ann's 4.A1 model/interface, then integrate draft reads (4.A2), with
   status/deadline metadata and locked snapshots after submission.
3. Implement submission recording (4.D3/4.A3), then closure (4.D4/4.A4), each
   with local API and portable acceptance tests.
4. Run on Launchpad with explicit reset permission, then obtain both directions
   of cross-team evidence after Quincy's Orbit release. Phase 3's 55/55 result
   does not establish Phase 4 conformance.

## Waiting on

- **Ann:** a published recorded-report model/interface (4.A1). No such model or
  open feature PR was present in `cra-service` at the start of this session.
- **Pod:** any answers to Q1-Q10 and the contract freeze. Richard has no private
  updates beyond GitHub. Both repos were checked: `pod-k-shared` main is
  `87e9571`, the contract remains `0.1.0-draft` and byte-identical to the service
  contract, and shared PR #8 still has no review or discussion comments.

## Notes for the next session

- Keep early-warning countries/versions strict until Team 21 approves Q9.
- Q3 still describes proposed behavior for never-reportable/resolved draft
  reads. Resolve or explicitly document the agreed fallback before the endpoint.
- Both owners edit `core/tickets.py`; keep increments small.
- Team 17 tests on Launchpad with permission; Quincy controls Orbit releases.
- Preserve the original checkout's local Gradescope draft. Do not mistake its
  old Phase 3 branch for the latest main or overwrite uncommitted work there.
