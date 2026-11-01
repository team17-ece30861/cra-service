# Handoff: Richard (Domain Logic and Testing)

**Last updated:** 2026-11-01 by Codex (Richard's session).

## Where things stand

Draft reads use the merged ReportSubmission model, status helper and migration unchanged. Live Model C drafts and locked stored snapshots have auth, resource/state and read-only checks; reporter fields are excluded.

The base is main 3c518a9, with merged PR75/76 foundations preserved. This branch
contains only task 4.A2 and companion tests/docs, not the full Phase 4 stack.

## In progress

- Branch: codex/phase4-draft-reads; prepared for an explicitly authorized draft PR.
- The merged-foundation draft/model/helper/upgrade regression passed 310 tests on SQLite. PostgreSQL CI and the required posted independent review remain pending. Stored rows are fixtures, not proof of submission POST.
- A fresh local review of the combined integration found no actionable issues;
  that is not posted approval of this PR. No merge/deployment/shared reset authorized.

## Next up

Review this one-task PR and CI before any merge. Submission recording and closure remain separate increments; Ann's 4.A5 ticket/list integration remains separate.

## Waiting on

- Posted review and CI/PostgreSQL results. Ann owns response/list/filter/privacy work.
- Richard's separate authorization before any merge or shared deployment reset/test.

## Notes for the next session

Q3 returns 409 for never-reportable tickets and keeps resolved drafts readable. Q4 uses current deadlines with locked content. Both remain documented proposals, not new pod agreement.
Only Quincy launches Orbit. Preserve the original checkout and its local report.
