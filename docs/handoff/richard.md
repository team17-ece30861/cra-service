# Handoff: Richard (Domain Logic and Testing)

**Last updated:** 2026-11-20 by Codex with Richard.

## Where things stand

Phase 4 is delivered. Main remains `ecb59a7`; no merge or deployment was
performed. Richard authorized publishing the Phase 5 model-coverage draft and
checking PostgreSQL CI, then implementing the HTTP test gaps separately. He has
now authorized publishing the HTTP draft and fixing operation reporting separately.
Remote reset tests, performance/restart runs and merges remain separate actions.

## In progress

- Model coverage: draft [PR #106](https://github.com/team17-ece30861/cra-service/pull/106),
  `codex/phase5-model-coverage`, in `work/cra-publish-t5`. Full Linux/PostgreSQL 18
  CI passed 1,494 tests on the final compatibility commit `81a05eb`; inspect its
  current-head CI on the PR before merging. The fixed
  44-requirement/266-scenario inventory and counting rules are unchanged.
- Mapping publication/configuration and exact own-target URL confirmation still
  need Quincy. Until an accessible mapping is configured, own model counts are
  null with a reason; other-team reports omit model. No deployed result is claimed.
- HTTP gaps: prepared for authorized draft publication on `codex/phase5-http-gaps`,
  based directly on main in the reused `work/cra-publish-t6`. New `http_gap_cases.py` plus
  remote and Django wrappers supply 19 portable cases: AC-07 edits, complete
  deadline/next-due and exact audit checks, rejected-write rollback, PATCH/triage
  404/413 precedence, and successful clock release.
- These 19 pass through Django and real isolated loopback WSGI HTTP. Selected
  regression: 197 passed, one existing PostgreSQL-only triage-concurrency skip.
  No skip was added. The full portable suite collects 241 tests.
- A temporary validation copy combined #106 and these HTTP files: 26 focused
  model-hook/HTTP tests passed. Its nested portable run passed 240 cases with
  the one expected HTTPS-only skip, retaining the original model expectations.
  New HTTP scenarios have no model bindings; do not inflate model coverage.
- Independent local review corrected a clock-release false pass and a missing
  `next_due_at` assertion; re-review found no remaining code issue. The stale
  README count was also corrected. The reviewer is closed. This is not a posted
  PR approval.

## Next up

1. Check #106's exact-head CI; obtain posted independent review and Quincy's
   platform/configuration review before any separately authorized merge.
2. Verify the authorized HTTP draft's current Linux/PostgreSQL CI and obtain
   posted independent review before any separately authorized merge. Preserve the collector
   test's suite-size compatibility correction when integrating the two changes.
3. Finish 5.10's operation-table partial-run/setup-failure fixes; shared fixtures
   and the pod's multiple-problem 422 decision remain outstanding.
4. 5.1: agree the load protocol before building the script; Quincy runs deployed
   performance/restart work. 5.4/5.6 still need full and cross-team evidence.

## Waiting on

Quincy: accessible version-pinned model mapping/manifest, configured mapping URL,
confirmed service bases, authorized Launchpad verification and Orbit/shared-copy
release. Ann/Team 21: remaining contract decisions and shared fixtures. No
Launchpad, Orbit or Team 21 reset test was run this session.

## Notes for the next session

The HTTP clock-release oracle brackets service clock/receipt values with the
runner's independent wall clock, allowing 120 seconds of skew; synchronize both
real clocks. It verifies advancement and restores FIXED in finally. This is not
the deployed tester's cleanup/isolation fix.

The first socket attempt failed with sandbox WinError 10013; the permitted client
to a sandbox server then timed out with WinError 10060. A permitted same-environment
server/client run passed 19/19. Failed artifacts were preserved separately.
The test server was stopped. This SQLite/WSGI result does not establish deployed
Gunicorn/Neon behavior.

Evidence in the parent workspace: `work/phase5-http-live-20261120-c.json`,
`work/phase5-http-live-20261120-c-operations.md`,
`work/phase5-http-regression-20261120-final.xml`, and
`work/phase5-combined-20261120-a.xml`. Model CI metadata/logs are in
`work/phase5-model-ci.json` and `work/phase5-model-job-*.log`.

No production API code, auth, root contract, workflow, migration, other teammate's
handoff or shared repository was changed by the HTTP increment. The user's original
checkout and earlier branches are preserved. Do not claim all Phase 5 is complete.
