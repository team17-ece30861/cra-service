# Handoff: Richard (Domain Logic and Testing)

**Last updated:** 2026-11-01 by Codex (Richard's session).

## Where things stand

Merged PR75/76 foundations are unchanged. PR77 adds draft reads; PR78 adds pure
submission validation. This branch adds only 4.A3 submission recording on them.

## In progress

- codex/phase4-record-submission is stacked on codex/phase4-validate-submission.
  Richard approved stacked drafts, not merge/deployment/shared reset.
- Actual rows, safe report_submitted audits and locked Draft responses use one
  clock value and a ticket lock. Existing transaction/savepoint protects rollback.
- 63 portable recording cases and 12 local storage/fault/concurrency cases; genuine
  duplicate race requires PostgreSQL CI. Combined local regression: 711 passed,
  four PostgreSQL skips. CI/posted approval still required for this PR.
- Combined localhost suite: 182 passed, one WinError 10053 transport failure,
  one skip. Same abort reproduced without CRA/Django; do not hide it or claim a
  green HTTP run. Investigate the real Linux stack with Quincy when authorized.

## Next up

Check CI and obtain posted independent review. Closure is a later task; Ann's
4.A5 Ticket/list status/metadata/next_due_at/filter wiring remains separate.

## Waiting on

PostgreSQL CI/review, owner integration and Richard's separate merge/reset go.

## Notes for the next session

401/413/404/400/409/422 precedence, no partial writes; Q5 adds no cross-report
chronology. Q3/Q4 remain proposals. Only Quincy launches Orbit.
