# Handoff: Richard (Domain Logic and Testing)

**Last updated:** 2026-11-01 by Codex (Richard's session).

## Where things stand

PR75/76 foundations unchanged. Authorized stack: #77 draft reads, #78 submission
rule, #79 recording, #80 closure rule, then this 4.A4 close endpoint. Each diff
is one task with companion docs. No merge/deployment/shared reset authorized.

## In progress

- codex/phase4-close-ticket stacks above codex/phase4-validate-closure; Richard
  explicitly approved stacked draft bases, not merging into those bases.
- Three reports required; atomic closed/resolved plus one audit. Existing writers
  reject closed tickets; resolved reads and snapshots stay available/unchanged.
- 34 portable and 11 local closure checks. Focused combined SQLite: 711 passed,
  four PostgreSQL skips. Full localhost HTTP: 182 passed, one Windows 10053 abort,
  one skip. Minimal WSGI without CRA/Django reproduces it; not hidden or rerun to green.
- PostgreSQL CI and posted PR approval are required, separate from local review.

## Next up

Check CI, especially duplicate submission/closure and final-recording/close races.
Obtain posted review and a new merge go. Retarget through main as prerequisites
land; never merge these drafts into feature bases. Ann's 4.A5 remains separate.

## Waiting on

CI/review, Ann's response/list/filter/privacy work, Quincy/pod coordination and
Richard's separate merge or shared reset permission.

## Notes for the next session

Q3/Q4 proposals/assumptions; Q5 only published awareness-to-now, Q9 strict.
AC-12 uses an actual title update, not Q6 no-op. Only Quincy launches Orbit.
