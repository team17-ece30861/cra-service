# Phase 5 report: Team 17's answers (DRAFT)

Draft answers for the Phase 5 document, built on [phase4.md](phase4.md). Every `[TBD: …]`
is a number or link that comes from the final Orbit launch and the runs after it; nothing
here is filled in from memory. Evidence for each claim is in [`docs/system.md`](../system.md).
Citation numbers follow the reference list in Q9 ([1] is the Cyber Resilience Act).

Cover page version: `[TBD: Orbit commit SHA]`, launched `[TBD: date/time ET]`.

## Q1.1 Increment description

**Delivered capability:** Phase 5 finishes the service as a stable final version. Through the common HTTPS interface, a client can now rely on the service with a realistic workload: with 1,000 tickets stored, 95% of requests finished within `[TBD: p95]` seconds on the evaluation deployment (target 1 s), and tickets, recorded reports and audit logs are unchanged after the service is restarted. Invalid input is now checked at scale by our own suite: `[TBD: N]` requests generated from the OpenAPI contract all received documented errors and none caused a server error or stored data. Three pod answers are now in force: a ticket submitted with a fix time in the future is rejected with 422, an early warning can be recorded with member states marked `["unknown"]` when they aren't known yet, and the final report deadline is defined from the first corrective or mitigating measure. Our console, the team's own intake channel, now saves without reloading the page and locks a username after five failed sign-ins. Our deployed tester now also reports how much of our own design it checked (model coverage), runs one suite at a time, and cleans up the target after each run. **Users/stakeholders:** the manufacturer's product security and compliance staff, who need the service to answer quickly and never lose a recorded report; Team 21 and the course staff, who test the service through the common interface and our deployed tester. **Regulatory provision(s):** the early warning, notification and final report obligations and their deadlines [1, Art. 14(1)-(2)(a)-(c)], including the measure that starts the final report clock [1, Art. 14(2)(c)], and the duty to keep records of vulnerability handling [1, Annex I, Part II(1)-(2)] `[TBD: confirm Annex reference wording before submitting]`.

REQ-17 - Performance │ Status: `[TBD: complete / partial]` │ Demonstrated by: AC-18 (`acceptance/perf.py` against the evaluation deployment: `[TBD: run/p95]`) `[TBD: if partial: what is missing]`

REQ-18 - Persistence │ Status: complete │ Demonstrated by: AC-19 (recorded demo, `scripts/restart_demo.sh`: a new Cloud Run revision replaced every instance and the ticket, report and audit log read back byte-for-byte unchanged; video `[TBD: link]`)

REQ-12 - Error handling │ Status: complete │ Demonstrated by: AC-02, AC-04, AC-13 (`[TBD: N]` generated malformed requests, `[TBD: test name]`), AC-14

REQ-01 - Intake │ Status: complete │ Demonstrated by: AC-01, plus the new future-fix-time rule (422) `[TBD: test names]`

REQ-04 - Deadlines │ Status: complete │ Demonstrated by: AC-03, AC-07; `fix.available_at` now means the first corrective or mitigating measure (wording change, no behavior change)

REQ-08 - Submission recording │ Status: complete │ Demonstrated by: AC-09, plus `["unknown"]` member states for the early warning `[TBD: test names]`

REQ-16 - Test controls │ Status: complete │ Demonstrated by: AC-17; our deployed tester now resets the target and releases its clock after each run

## Q1.2 Comparison with the Phase 2 plan

We delivered the Phase 5 milestone in Phase 2, Section 6.3: the performance target with 1,000 tickets (REQ-17, AC-18) `[TBD: met / measured at …]`, persistence across restarts (REQ-18, AC-19, recorded), each team's own intake channel (our console, delivered early in Phase 4 and finished now), and a stable final version with the full suite (AC-01 to AC-18) running in CI on every change and against Team 21 before the deadline. We also closed the four items that slipped from Phase 4: our own 500-plus generated malformed requests (AC-13), the server-error alert, the early performance check, and the pod follow-ups (the two contract changes Team 21 agreed to by email on November 1, the workaround question, and whether a 422 lists every problem). `[TBD: list anything not delivered, each with its own concrete cause — e.g. "X: not delivered because …"; if nothing, say "Nothing planned for Phase 5 was left out."]` There were no instructor-required scope changes. One process change: Team 21 hadn't approved the contract freeze PR or answered the workaround question by November 21, so Team 17 merged the agreed changes into the pod's shared repository on `[TBD: date]` and told Team 21 by `[TBD: channel]`; the workaround answer is our own decision and is listed as such in Q3.2.

## Q2.1 Deployed web service

Our service runs on Google Cloud Run [2] in the us-central1 region as a Docker container (Python 3.12, Django [4] with Django Ninja [5], served by gunicorn), backed by a managed Neon PostgreSQL database [3], with database credentials and per-client API tokens in Google Secret Manager [6]; the same service hosts our console at /console/. The health endpoint is https://team17-prod-7zneiwx4ba-uc.a.run.app/health (public, returns `{"status": "ok"}`). Every release is a container image labeled with the Git commit it came from: changes merged to main are tested in CI and deployed automatically to a development instance only our team uses, and the evaluation deployment changes only through a manual release step that reruns the tests, applies migrations, deploys, and checks the health endpoint; it now runs `[TBD: SHA]`, launched `[TBD: date]`. The service is reachable at all times but scales to zero when idle, so the first request after a quiet period takes about 3 to 6 seconds (plus about 1.5 s for the first database read) `[TBD: update with measured cold start from perf run]`; it would stop only if its $10 spending cap were reached, until we lift it by hand, and an alert now emails us on any server error. There's no rate limit, but it runs one instance handling two requests at a time with a 30-minute timeout and a 64 KB request limit; all clients share one database and one test clock, so test runs should be one at a time (our deployed tester now refuses a second run while one is going), and each team and the course staff have their own access token, which must be kept private.

## Q2.2 Registry and team documentation

Registry entry: Cross-team testing endpoint registry (Endpoint_Registry Google Sheet), Pod K, Team 17 row (system URL, our tester, the pod spec, access notes and time limits) │ Updated on: `[TBD: date]`

Team documentation: https://github.com/team17-ece30861/pod-k-shared/blob/main/team17/SYSTEM.md (the system as delivered in Phase 5: operations, the console, models, interfaces including the OpenAPI descriptions of our tester and test endpoints, the model-coverage mapping, test results, and known limitations; the source is docs/system.md in our repository) │ Updated on: `[TBD: date]`

## Q2.3 Operational experience supported by observability evidence

Our Phase 2 plan held through the final phase: tickets, recorded reports and audit entries live in a persistent Neon PostgreSQL database that survives restarts and redeploys (shown by the AC-19 recording) and changes only through the API, the console, or the pod's test reset, which clears tickets, reports and audit entries but keeps test sessions; our deployed tester now resets the target and releases its clock after each run. Secrets live in Google Secret Manager and are injected at deploy time, one API token per client, and GitHub Actions deploys through Workload Identity Federation [7] without stored keys. To detect failures, the access log records every request with the name of the client whose token matched (never the token), the application logs rejected requests and a stack trace without request data for any server error, Cloud Run's request log records status and latency, and, new this phase, a Cloud Monitoring alert emails the team within 5 minutes of any 5xx response on either deployment (the one change from the Phase 2 plan, which had no automated alert). Since the Phase 5 release, the evaluation deployment has logged `[TBD: N]` server errors and `[TBD: N]` client errors.

Excerpt from the evaluation deployment `[TBD: date/time ET; times in UTC]`:

```
[TBD: 3-5 lines from Cloud Logging during the AC-18 run: access log line(s) with client name, a Cloud Run request log line with latency, and the alert policy's existence/incident]
```

## Q3.1 Operation status

`[TBD: regenerate from the deployed tester's run against Orbit at the cover-page SHA. Same 15 operations as Phase 4 (health, 9 ticket operations, 4 test-control operations); update: POST /tickets error codes now include 422 (future fix time), PATCH/triage 404 and 413 are now checked by the HTTP tester (#107), DELETE /test/clock success is now checked.]`

Integration: Phase 5 added no new operations. The future-fix-time rule and `["unknown"]` member states are in the existing validation and domain rules that the API and the console share; the console's sheets now post to the same views with a request that returns the updated page regions instead of a redirect; the console sign-in records failed attempts in a new table; and our deployed tester gained a run lock, recovery of runs cut off by a restart, cleanup of the target, and model coverage for runs against our own system. A request still flows: Google's front end → Cloud Run → gunicorn → our auth/X-Actor/size middleware → the Ninja route → pure domain rules in `core/domain/` → PostgreSQL, with the audit entry written in the same transaction.

## Q3.2 Contract changes and pod communication

**Contract version at delivery:** `[TBD: 0.3.0]` (pod-k-shared `openapi.yaml`, identical to our repository's copy and our published tester's copy).

**Changes since Phase 2:** 0.2.0 records the agreed clarifications from Phase 4 (Q1 to Q6 and Q10, wording only). 0.3.0 adds: (1) `POST /tickets` returns 422 when `fix.available_at` is later than now (Q7), because the field list already said "not later than now" but the operation listed no 422; (2) `member_states` may be `["unknown"]` so an early warning can be sent before the affected Member States are known, because Art. 14(2)(a) [1] asks for them only "where applicable" (Q9); (3) `fix.available_at` is defined as the first corrective or mitigating measure, because Art. 14(2)(c) [1] starts the final report clock at either (Q8, wording only); (4) a 422 lists every business-rule problem found (both teams already did this).

**Pod agreement:** Q1 to Q6 and Q10, Q7 and Q9 were agreed by Team 21 by email on November 1, 2026 (replying to our October 27 email); Team 21's own tests already expect the Q7 and Q9 behavior and the 422 list. Q8 was asked in the same October 27 email and not answered, so it is Team 17's decision; Team 21 was told by `[TBD: channel, date]`. Team 17 merged both contract PRs (pod-k-shared `[TBD: #14 and #N]`) on `[TBD: date]`.

**Intentional deviations and resolution plan:** `[TBD: after Q7/Q9 merge and Orbit launch: if all is live, write "None: the evaluation deployment implements contract 0.3.0 as published." If Team 21 objects to Q8, list it here with the plan.]`

## Q4.1 Test runner and execution instructions

**Base URL override:** Point the suite at https://team17-prod-7zneiwx4ba-uc.a.run.app (the base URL, no path prefix) and send "Authorization: Bearer <token>" on every request except GET /health. Our own tester takes any team's base URL through the CRA_BASE_URL environment variable or the --base-url option, with no code changes, and our deployed tester takes it as `target_url` in POST https://team17-prod-7zneiwx4ba-uc.a.run.app/tester/test/setup. │ **Response received:** `[TBD: GET /health → 200 {"status":"ok"}; an authenticated GET /tickets → 200 with a JSON array, captured on date]` │ **Conforms to spec:** yes

**Known deviations from the OpenAPI spec:** `[TBD: "none" once 0.3.0 is merged and deployed; must match Q3.2]`

## Q4.2 Tests for new functionality

`[TBD: test names from the merged PRs]`

AC-18 │ Requirement(s): REQ-17 │ Test(s): `acceptance/perf.py` (1,000 tickets, 200 sequential mixed requests, every status checked; fails on p95 > 1 s or any unexpected status); `tests/test_perf_script.py` (percentiles, mix, a fast 500 still fails); `tests/test_query_counts.py` (list and detail stay at a fixed number of queries at 1,000 tickets) │ Type: boundary (1,000 tickets), failure (unexpected status) │ Automated: yes (run against a deployment on demand, not in CI, because it loads 1,000 tickets)

AC-19 │ Requirement(s): REQ-18 │ Test(s): `scripts/restart_demo.sh` (create, triage, record, force a new revision, compare byte-for-byte) │ Type: success │ Automated: scripted, shown by recorded demo as the spec requires ("Recorded demo by the owning team")

AC-13 │ Requirement(s): REQ-12 │ Test(s): `[TBD]` (≥500 generated malformed requests in CI against the in-process app) and `acceptance/malformed.py` against the deployment │ Type: failure │ Automated: yes

AC-07 │ Requirement(s): REQ-06 │ Test(s): `[TBD: http_gap_cases names from #107]` │ Type: success, failure │ Automated: yes (now in the HTTP tester too)

Q7 (REQ-01), Q9 (REQ-08) │ Test(s): `[TBD]` │ Type: failure (422), boundary (equal to now), success (`["unknown"]`) │ Automated: yes (CI only; kept out of the cross-team suite)

Console lockout (LIM-12) and no-reload saves (5.7) │ Test(s): `[TBD]` │ Automated: yes (server tests), plus browser screenshots at 1280 and 390 px

**Oracles:** As in earlier phases, expected values come from the pod spec worked out by hand, never from our service's output: deadlines from Model D, required fields from Model C, status codes and their order from the OpenAPI contract, which our tester uses to validate every response. AC-18's oracle is the spec's own threshold (p95 ≤ 1 s) on latencies measured by the client, with a status check on every request so a fast error can't pass; AC-19 compares the raw responses before and after the restart byte-for-byte; AC-13's oracle is the contract itself (any 2xx or 5xx, an undocumented status, a non-problem+json body, or a changed row count fails).

## Q4.3 Regression and static checks

Every push and pull request runs our full CI pipeline in GitHub Actions, and nothing deploys unless it passes `[TBD: count runs on main and failures this phase]`. The pipeline runs the complete test suite against PostgreSQL 18, which re-runs every earlier platform, unit and integration test and the whole portable acceptance suite (AC-01 to AC-17 plus the new AC-07 HTTP cases and the generated AC-13 run) in-process, so a change that breaks earlier behavior can't merge; the same acceptance cases run over HTTP against the deployments through our deployed tester. Every code change also gets an independent review by a teammate or a fresh AI session before it merges.

CI run: `[TBD: link to a main run at the cover-page SHA]`

## Q4.4 Static checks

Our static checks are unchanged since Phase 3 except for one addition: CI still runs ruff (linting and formatting), a check for missing migrations, Django's system checks, and contract validation of every tester response, and Dependabot alerts and secret scanning with push protection are on; new this phase, Schemathesis validates the OpenAPI file and generated requests against it in CI. We still don't use a type checker or pre-commit hooks. A failing check blocks merging and deploying.

CI run: `[TBD: same link]`

## Q4.5 Test results against the deployed system

Run date/time: `[TBD]` │ Version tested: `[TBD: SHA = cover page]` │ Tests run: `[TBD]` │ Passed: `[TBD]` │ Failed: `[TBD]` │ Skipped: `[TBD]`

`[TBD: "Failures: none." or one line per failure: test │ classification │ cause │ plan. This is the final phase, so a plan can't name a later phase: say what we did or what a user should do.]` Also: AC-18 `[TBD: p50/p95/max, n=200, 1,000 tickets, cold start separately]`; AC-13 `[TBD: N requests, 0 server errors]`.

## Q5.1 Model updates

Model A: Ticket lifecycle (state machine) │ Changed: no │ What changed and why: Phase 5 added no states or transitions; the Phase 4 version matches the delivered service. │ Location: https://github.com/team17-ece30861/cra-service/tree/main/docs/models

Model B: Report status (state machine) │ Changed: no │ What changed and why: unchanged since Phase 4. │ Location: same

Model C: Required fields per draft (table) │ Changed: yes │ What changed and why: the early warning's member states may now be `["unknown"]`, which counts as present, because Art. 14(2)(a) [1] asks for them only "where applicable" (pod Q9). │ Location: `[TBD: docs/spec.md / pod-k-shared spec.md section]`

Model D: Deadline examples (table) │ Changed: no (wording) │ What changed and why: the examples are unchanged; the definition of the fix time now says "first corrective or mitigating measure" (Q8), which doesn't change any example. │ Location: pod-k-shared spec.md

Architecture and data flow (component diagram, Section 7.1) │ Changed: yes │ What changed and why: `[TBD: add the console sign-in attempts table, the tester's run lock and cleanup step, and the monitoring alert, if drawn; keep only what exists]` │ Location: docs/models/architecture.png

Design requirements and model coverage: our 44 design requirements and how each maps to tests are in `[TBD: commit-pinned link to docs/model-coverage.md]`; our tester reports `coverage.model` against our own system (`[TBD: covered]`/44 at the cover-page SHA).

## Q5.2 Model-implementation consistency

`[TBD: method — the model-coverage mapping now checks this automatically on every run against our own system (each design requirement counts only when every scenario bound to it was evaluated), plus a fresh AI session traced each changed model element to code. Divergence found this phase: (pick a real one from the work, e.g. Model C's strict early-warning fields vs. Art. 14(2)(a), corrected in the model and the code together, per Q9).]`

## Q6.1 Cross-team test

`[TBD after tonight's runs]`

Our tests → Team 21 service │ Date: `[TBD]` │ Run/passed: `[TBD]` │ Main problem and owner: `[TBD]` │ Coverage: code: `[TBD from their /test/report or "not available: …"]`; component: `[TBD]`; system: `[TBD: N of 19 ACs]`

Team 21 tests → our service │ Date: `[TBD]` │ Run/passed: `[TBD]` │ Main problem and owner: `[TBD]` │ Coverage: `[TBD]` │ Note: run by Team 17 using Team 21's published tester (pod-k-shared team21/tester, commit `[TBD]`) against our evaluation deployment `[TBD: say exactly how it was run]`

## Q6.2 Specification issues discovered

Issue: The final report deadline (REQ-04, `fix.available_at`): Art. 14(2)(c) [1] starts the 14-day clock when a corrective or mitigating measure is available, but the spec only said "fix". │ Effect: a team that recorded a workaround as something other than the fix would compute a final report due date later than the regulation allows; tests based on Model D couldn't tell the difference. │ Pod decision or plan: defined as the first corrective or mitigating measure in contract `[TBD: 0.3.0]` on `[TBD: date]` (wording only; no example changes). Asked in our October 27 email; Team 21 didn't answer, so this is Team 17's decision and we told them on `[TBD]`.

## Q7.1 What changed and what remains incomplete

Changed since Phase 2:
- Deployed on Google Cloud Run with Neon PostgreSQL, per-client tokens, X-Actor, a 64 KB limit and contract-format errors in the agreed precedence (REQ-12, REQ-14; AC-02, AC-15); intake, triage, deadlines and updates (REQ-01 to REQ-04, REQ-06; AC-01, AC-03 to AC-05, AC-07, AC-14) in Phase 3.
- The full reporting workflow in Phase 4 (REQ-05, REQ-07 to REQ-11, REQ-15; AC-06, AC-08 to AC-12, AC-16) and the console.
- New in Phase 5: performance measured with 1,000 tickets (REQ-17; AC-18), persistence shown across a restart (REQ-18; AC-19), our own generated malformed-request run (REQ-12; AC-13), the Q7/Q8/Q9 contract changes (REQ-01, REQ-04, REQ-08), the server-error alert, the console's in-place saves and sign-in lockout, and the tester's model coverage, run lock, restart recovery and cleanup (REQ-16).

Remaining incomplete:
- `[TBD: anything not delivered, with REQ/AC IDs; must match Q1.1 and Q3.1. If none: "Nothing from the pod's planned scope remains incomplete."]`

## Q7.2 Known limitations and defects

`[TBD: carry LIM-01..LIM-13 from Phase 4, closing what Phase 5 fixed:]`
- LIM-01 shared database and clock: still true (by design of the shared test controls); our tester now runs one suite at a time.
- LIM-02 scale to zero / single instance: update with AC-18 numbers and measured cold start.
- LIM-03: alert now exists; the $10 cap remains.
- LIM-04 (Q8): fixed by contract 0.3.0 wording.
- LIM-05 (Q7/Q9): fixed in 0.3.0 `[TBD if live]`.
- LIM-06 (freeze PR): fixed when #14 merged.
- LIM-07 empty list audit: `[TBD: still open?]`
- LIM-08 no rate limiting: still open.
- LIM-09 health doesn't check the DB / HEAD needs a token: `[TBD]`
- LIM-10 Google front end rejects GET with a body: unchanged (platform).
- LIM-11 test gaps: closed by #107 and AC-13 `[TBD]`.
- LIM-12 console lockout: fixed `[TBD]`.
- LIM-13 tester cleanup: fixed `[TBD]`.
Target phase: this is the final phase, so each open item states "none planned" with the workaround.

## Q7.3 Adjustments to next phase milestone

Phase 5 is the last milestone in Phase 2, Section 6 (6.1 to 6.3 cover Phases 3 to 5), so there is no next milestone to adjust; the final version is `[TBD: SHA]`. Priority risks from Phase 2, Section 9.1:
- Risk 1 (our reading of the CRA): reduced. The two findings from our CRA review are now in the contract: early warnings can be sent with unknown member states, and the final report clock starts at the first corrective or mitigating measure [1, Art. 14(2)].
- Risk 2 (cross-team compatibility): `[TBD: reduced/closed with tonight's numbers]`.
- Hosting performance: `[TBD: closed by AC-18 numbers, or remains with the measured gap]`.
- New risk, now realized and handled: pod responsiveness at the end of the course. Team 21 didn't answer the last open question or approve the freeze, so Team 17 merged the agreed changes and recorded Q8 as its own decision; a podmate could still disagree after the deadline.

## Q8.1 Actual GenAI use

`[Each teammate writes their own: Quincy, Ann, Richard.]`

## Q9 References

[1] European Parliament and Council of the European Union. "Regulation (EU) 2024/2847 (Cyber Resilience Act)." October 23, 2024. https://eur-lex.europa.eu/eli/reg/2024/2847/oj. Accessed: 2026-11-22.

[2] Google Cloud. "Cloud Run documentation." https://docs.cloud.google.com/run/docs. Accessed: 2026-11-22.

[3] Neon. "Neon documentation." https://neon.com/docs/introduction. Accessed: 2026-11-22.

[4] Django Software Foundation. "Django documentation." Version 5.2. https://docs.djangoproject.com/en/5.2/. Accessed: 2026-11-22.

[5] Django Ninja. "Django Ninja." Version 1.x. https://django-ninja.dev/. Accessed: 2026-11-22.

[6] Google Cloud. "Secret Manager documentation." https://docs.cloud.google.com/secret-manager/docs. Accessed: 2026-11-22.

[7] Google Cloud. "Workload Identity Federation." IAM documentation. https://docs.cloud.google.com/iam/docs/workload-identity-federation. Accessed: 2026-11-22.

[8] Schemathesis. "Schemathesis documentation." `[TBD: version]`. https://schemathesis.readthedocs.io/. Accessed: 2026-11-22. `[TBD: cite in Q4.2/Q4.4 text]`

[9] Google Cloud. "Cloud Monitoring: alerting overview." https://docs.cloud.google.com/monitoring/alerts. Accessed: 2026-11-22. `[TBD: cite in Q2.3]`
