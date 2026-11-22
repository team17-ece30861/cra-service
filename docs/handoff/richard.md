# Handoff: Richard (Domain Logic and Testing)

**Last updated:** 2026-11-21 by Codex with Richard.

## Where things stand

Main remains `ecb59a7`. Richard authorized publishing the HTTP-test draft and
checking PostgreSQL CI, then fixing operation reporting separately. On November
21 he also authorized the reporting branch's commit, push, draft PR and CI.
No merge,
deployment, shared reset, performance run or restart was performed.

## In progress

- Model coverage: draft [#106](https://github.com/team17-ece30861/cra-service/pull/106),
  `codex/phase5-model-coverage`, head `81a05eb`; PostgreSQL 18 CI passed 1,494.
  Mapping/manifest publication, configured mapping URL and own-target confirmation
  still need Quincy. The fixed 44-requirement baseline is unchanged.
- HTTP tests: draft [#107](https://github.com/team17-ece30861/cra-service/pull/107),
  `codex/phase5-http-gaps`, head `5c616b7`; PostgreSQL 18 CI passed 1,424.
  Its 19 new cases previously passed isolated local HTTP; standalone collection
  is 241. No deployed HTTP run is claimed. Original checkout/branches are preserved.
- Operation reporting: draft [#108](https://github.com/team17-ece30861/cra-service/pull/108),
  `codex/phase5-operation-reporting`, based on main, in the reused
  `work/cra-publish-a4` checkout. Published November 21; inspect its exact-head
  PostgreSQL CI before merging. Failed setup checks
  survive even if the Service fixture raises before returning. Conforming setup
  responses are inconclusive; successful fixture setup supplies no passing credit.
- Completion uses collection, scope, outcomes and teardown. Early stops, code-0
  exits before completion, -k/positional filters, --ignore/--ignore-glob exclusions,
  collection failures and interruptions show incomplete with counts/reasons.
  A fully attempted suite may finish with failures. Existing result fields and
  course API are preserved; extra completion fields are standalone-report metadata.
- Selected local regression: 191 passed, one existing PostgreSQL-only triage skip.
  Lint/format, Django, migration and whitespace checks pass. No new skip was added.
- Independent local review caught positional and collection-exclusion omissions.
  Both are fixed with real pytest child cases; final re-review found no remaining
  actionable issue. The reviewer is closed; no posted PR approval is claimed.
- Final combined validation with #106/#107 passed 208 focused tests, including
  both model and operation hook families and the exclusion-filter correction.
  Its nested portable suite passed 240/241, with the expected HTTPS-only skip;
  this is local in-process evidence, not deployed HTTP or PostgreSQL evidence.

## Next up

1. Verify #106/#107/#108 current-head CI and obtain posted independent reviews before
   separately authorized merges. Quincy reviews model/interface configuration.
2. As checked November 21, none of the three drafts has a posted review or PR
   comment. Local independent review is not posted approval. Draft publication
   does not authorize merging or a release.
3. Reconcile overlapping client/plugin and handoff changes when integrating the
   independent main-based branches; keep model journaling/call-phase evidence and
   operation setup evidence/completion hooks. A temporary tested merge is not a
   branch merge or deployment.
4. Finish 5.10 shared fixtures and the multiple-problem 422 decision; 5.1 needs
   an agreed load protocol and script, then Quincy's performance run. 5.4/5.6
   still need fresh deployed and both-direction cross-team evidence.

## Waiting on

Quincy: mapping/manifest publication and configuration, service-base confirmation,
release coordination and authorized Launchpad verification. Ann/Team 21: remaining
contract decisions/shared fixtures. Only Quincy launches Orbit.

## Notes for the next session

Reporting evidence is in the parent workspace:
`work/phase5-reporting-regression-20261120-final2.xml` and
`work/phase5-reporting-combined-20261120-final2.xml`.
The temporary combined source is `work/phase5-reporting-combined-20261120-c`.
HTTP CI is [run 44778121863](https://github.com/team17-ece30861/cra-service/actions/runs/44778121863).
Its saved log is `work/phase5-http-job-136433295330.log`.

The portable public copy needs the new `observations.py` alongside client/plugin
updates, coordinated with Quincy's release. No production API code, auth, root
contract, workflow, migration, other teammate's handoff or shared repo was changed.
Known Windows full-suite blockers were not disabled or repaired. Local SQLite,
Linux/PostgreSQL CI and deployed HTTP remain different evidence categories.
