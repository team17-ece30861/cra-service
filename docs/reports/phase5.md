# Phase 5 report: Team 17's answers

Answers for the Phase 5 document, built on [phase4.md](phase4.md). Evidence for each claim
is in [`docs/system.md`](../system.md) ("Recorded runs"). Citation numbers follow the
reference list in Q9 ([1] is the Cyber Resilience Act).

Cover page version: `c875f14` (evaluation deployment revision `team17-prod-00011-qqg`),
launched November 22, 2026, 12:12 PM Eastern.

## Q1.1 Increment description

**Delivered capability:** Phase 5 finishes the service as a stable final version. Through the common HTTPS interface, a client can now rely on the service with a realistic workload: with 1,000 tickets stored, 95% of requests finished within 0.74 seconds on the evaluation deployment (target 1 s), and tickets, recorded reports and audit logs read back unchanged after the service was restarted. Invalid input is now checked at scale by our own suite: 683 requests generated from the OpenAPI contract all received the documented error, and none caused a server error or stored anything. Three pod answers are now in force: a ticket submitted with a fix time in the future is rejected with 422, an early warning can be recorded with member states marked `["unknown"]` when they aren't known yet, and the final report deadline is defined from the first corrective or mitigating measure. Our console, the team's own intake channel, now saves without reloading the page and locks a username after five failed sign-ins. Our deployed tester now also reports how much of our own design it checked (model coverage), runs one suite at a time, and cleans up the target after each run. **Users/stakeholders:** the manufacturer's product security and compliance staff, who need the service to answer quickly and never lose a recorded report; Team 21 and the course staff, who test the service through the common interface and our deployed tester. **Regulatory provision(s):** the early warning, notification and final report obligations and their deadlines [1, Art. 14(1)-(2)(a)-(c)], including the measure that starts the final report clock [1, Art. 14(2)(c)] and the member states named "where applicable" in the early warning [1, Art. 14(2)(a)].

REQ-17 - Performance │ Status: complete │ Demonstrated by: AC-18 (`acceptance/perf.py` against the evaluation deployment at `c875f14` on November 22, 2026: 1,000 tickets, 200 requests one at a time, p95 736 ms, 0 unexpected responses)

REQ-18 - Persistence │ Status: complete │ Demonstrated by: AC-19 (recorded demo of `scripts/restart_demo.sh prod`: a new Cloud Run revision replaced every instance, and the ticket, early-warning report and audit log read back byte-for-byte unchanged; video: https://purdue0-my.sharepoint.com/:v:/g/personal/qdeklerk_purdue_edu/IQCXXwEfxLuSQ49vvVBqK75hAWZo_IIdPbXZwQyBD67BozA?e=eBzr8P)

REQ-12 - Error handling │ Status: complete │ Demonstrated by: AC-02, AC-04, AC-13 (683 generated malformed requests against the evaluation deployment with `acceptance/malformed.py`; 664 in CI in `tests/test_malformed_requests.py`), AC-14

REQ-01 - Intake │ Status: complete │ Demonstrated by: AC-01, plus the new future-fix-time rule (422) in `tests/test_contract_030.py::TestSubmitFutureFixTime`

REQ-04 - Deadlines │ Status: complete │ Demonstrated by: AC-03, AC-07; `fix.available_at` now means the first corrective or mitigating measure (wording change, no behavior change)

REQ-08 - Submission recording │ Status: complete │ Demonstrated by: AC-09, plus `["unknown"]` member states for the early warning in `tests/test_contract_030.py::TestUnknownMemberStates` and `::TestUnknownMemberStatesInReports`

REQ-16 - Test controls │ Status: complete │ Demonstrated by: AC-17; our deployed tester now resets the target and releases its clock after each run (`tests/test_tester_run_rules.py`)

## Q1.2 Comparison with the Phase 2 plan

We delivered the Phase 5 milestone in Phase 2, Section 6.3: the performance target with 1,000 tickets (REQ-17, AC-18, p95 736 ms on the evaluation deployment), persistence across restarts (REQ-18, AC-19, recorded), each team's own intake channel (our console, finished now), and a stable final version with the full suite running in CI on every change and against Team 21 before the deadline, plus the four items that slipped from Phase 4 (our own generated malformed requests for AC-13, the server-error alert, the early performance check, and the pod follow-ups Q7 to Q9). Nothing planned for Phase 5 was left out, and there were no instructor-required scope changes. One plan item needed rework for a concrete reason: AC-18 first failed on our development deployment early on November 22 (p95 1.37 s) because every request opened a new database connection (about 190 ms) and the full ticket list was 1.7 MB, so we kept connections open and compressed responses, after which it passed. One process deviation also had a concrete cause: Team 21 didn't review the contract PRs or answer the workaround question after their November 1 email, so on November 22 Team 17 merged the 0.2.0 freeze (pod-k-shared #14) and 0.3.0 (#20) itself, citing that email, and recorded the workaround answer as its own decision (Q3.2).

## Q2.1 Deployed web service

Our service runs on Google Cloud Run [2] in the us-central1 region, backed by a managed Neon PostgreSQL database [3], as a Docker container (Python 3.12, Django [4] with Django Ninja [5], served by gunicorn), with credentials and per-client API tokens in Google Secret Manager [6], and its public health endpoint is https://team17-prod-7zneiwx4ba-uc.a.run.app/health (returns `{"status": "ok"}`); the same service hosts our console at /console/. Every release is a container image labeled with the Git commit it came from: merges to main are tested in CI and deployed automatically to a development instance only our team uses, and the evaluation deployment changes only through a manual release step that reruns the tests, applies migrations, deploys and checks the health endpoint; it now runs `c875f14`, launched November 22, 2026. The service is reachable at all times but scales to zero when idle, so the first request after a quiet period takes about 3 to 6 seconds (plus about 1.5 s for the first database read), and it would stop only if its $10 spending cap were reached, until we lift it by hand (an alert now emails us on any server error). There's no rate limit, but it runs one instance handling two requests at a time with a 30-minute timeout and a 64 KB request limit; all clients share one database and one test clock, so test runs must be one at a time (our deployed tester refuses a second run while one is going), and each team and the course staff have their own access token, which must be kept private.

## Q2.2 Registry and team documentation

Registry entry: Cross-team testing endpoint registry (Endpoint_Registry Google Sheet), Pod K, Team 17 row (system URL https://team17-prod-7zneiwx4ba-uc.a.run.app, our tester at https://team17-prod-7zneiwx4ba-uc.a.run.app/tester, the pod spec, access notes and time limits) │ Updated on: November 22, 2026

Team documentation: https://github.com/team17-ece30861/pod-k-shared/blob/main/team17/SYSTEM.md (the system as delivered in Phase 5: models, interfaces including the OpenAPI descriptions of our tester and test endpoints, functionality, the model-coverage mapping, test results, and known limitations; the source is docs/system.md in our repository) │ Updated on: November 22, 2026

## Q2.3 Operational experience supported by observability evidence

Our Phase 2 plan held through the final phase: tickets, recorded reports and audit entries live in a persistent Neon PostgreSQL database that survives restarts and redeploys (shown by the AC-19 recording) and change only through the API, the console, or the pod's test reset, which clears tickets, reports and audit entries but keeps test sessions; our deployed tester now resets the target and releases its clock after each run. Secrets live in Google Secret Manager [6] and are injected at deploy time, one API token per client, and GitHub Actions deploys through Workload Identity Federation without stored keys; no secret is in the repository or this report. To detect failures, the access log records every request with the name of the client whose token matched (never the token), the application logs rejected requests and a stack trace without request data for any server error, Cloud Run's request log records status and latency, and, new this phase, a Cloud Monitoring alert [7] emails the team within 5 minutes of any 5xx response on either deployment (the one change from the Phase 2 plan, which had no automated alert). From the Phase 5 release to 1:33 PM Eastern on November 22, the evaluation deployment logged 0 server errors and 1,908 client errors, all from deliberate test runs (for example, the 683 malformed requests).

Excerpt from the evaluation deployment, November 22, 2026, end of the AC-18 run (12:26 PM Eastern; times in UTC):

```
169.254.169.126 - team17 [22/Nov/2026:17:26:19 +0000] "POST /tickets/ae30b079-8531-4a11-b337-b7b0a4da1d9e/close HTTP/1.1" 200 798 "-" "-"
169.254.169.126 - team17 [22/Nov/2026:17:26:20 +0000] "PATCH /tickets/49dad15b-7c65-4a97-a285-3fe842c38286 HTTP/1.1" 200 475 "-" "-"
2026-11-22T17:26:19.98Z  run.googleapis.com/requests  PATCH /tickets/49dad15b-…  status=200  latency=0.261s  size=794
2026-11-22T17:26:20.31Z  run.googleapis.com/requests  POST /tickets/673cf0a4-…/reports/early_warning/submission  status=200  latency=0.292s
Alert policy "Team 17: server errors on team17-prod" (any 5xx in 5 min → email): enabled, no incident since the release
```

## Q3.1 Operation status

Generated by our tester from its command-line run against the evaluation deployment at `c875f14` on November 22, 2026 (240 of 241 tests passed; the one error was a client-side network timeout, see Q4.5). "Checked" lists the status codes the tester observed for each operation, every response body was validated against the contract, and nothing is reported as passing that wasn't observed.

GET /health │ Requirement(s): none (public health check) │ Implemented: yes │ Success responses conform: yes │ Error responses conform: none defined in the contract

POST /tickets │ Requirement(s): REQ-01, REQ-12, REQ-13, REQ-14 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (400, 401, 413 checked over HTTP; the new 422 for a future fix time is checked in CI by `tests/test_contract_030.py` and kept out of the cross-team HTTP suite)

GET /tickets │ Requirement(s): REQ-10, REQ-15 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (400, 401 checked)

GET /tickets/{id} │ Requirement(s): REQ-04, REQ-05, REQ-15 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (401, 404 checked)

PATCH /tickets/{id} │ Requirement(s): REQ-04, REQ-06 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (400, 401, 404, 409, 413, 422 checked; 404 and 413 newly checked this phase)

POST /tickets/{id}/triage │ Requirement(s): REQ-02, REQ-03, REQ-04 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (400, 401, 404, 409, 413, 422 checked; 404 and 413 newly checked this phase)

GET /tickets/{id}/reports/{type} │ Requirement(s): REQ-07, REQ-15 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (401, 404, 409 checked)

POST /tickets/{id}/reports/{type}/submission │ Requirement(s): REQ-05, REQ-08 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (400, 401, 404, 409, 413, 422 checked)

POST /tickets/{id}/close │ Requirement(s): REQ-09 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (400, 401, 404, 409 checked)

GET /tickets/{id}/audit │ Requirement(s): REQ-11 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (401, 404 checked; 405 for editing or deleting the log is checked by a separate tester case outside this table)

POST /test/reset │ Requirement(s): REQ-16 │ Implemented: yes │ Success responses conform: yes (204) │ Error responses conform: yes (401 checked)

GET /test/clock │ Requirement(s): REQ-16 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (401 checked)

PUT /test/clock │ Requirement(s): REQ-16 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (400, 401 checked)

DELETE /test/clock │ Requirement(s): REQ-16 │ Implemented: yes │ Success responses conform: yes (204, now checked by a tester case) │ Error responses conform: yes (401 checked)

Integration: Phase 5 added no new operations. The future-fix-time rule and `["unknown"]` member states are in the existing validation and domain rules that the API and the console share; the console's sheets now post to the same views with a request that returns the updated page regions instead of a redirect; the console sign-in records failed attempts in a new table; the platform middleware now compresses API responses for clients that ask, and each worker keeps its database connection for 5 minutes; and our deployed tester gained a run lock, recovery of runs cut off by a restart, cleanup of the target, and model coverage for runs against our own system. A request still flows: Google's front end → Cloud Run → gunicorn → our token, X-Actor and size middleware → the Ninja route → pure domain rules in `core/domain/` → PostgreSQL, with the audit entry written in the same transaction.

## Q3.2 Contract changes and pod communication

**Contract version at delivery:** 0.3.0 (pod-k-shared `openapi.yaml`, identical to our repository's copy and our published tester's copy).

**Changes since Phase 2:** 0.2.0 records the Phase 4 clarifications (Q1 to Q6 and Q10, wording only), and 0.3.0 adds four changes: `POST /tickets` returns 422 for a `fix.available_at` later than now, because the field already said "not later than now" but the operation listed no 422 (Q7); `member_states` may be `["unknown"]`, because Art. 14(2)(a) [1] asks for them only "where applicable" (Q9); `fix.available_at` means the first corrective or mitigating measure, because Art. 14(2)(c) [1] starts the final report clock at either (Q8, wording only); and a 422 lists every business-rule problem found (both teams already did this).

**Pod agreement:** Team 21 agreed to Q1 to Q6, Q10, Q7 and Q9 by email on November 1, 2026 (replying to our October 27 email), while Q8 and the 422 rule went unanswered and are Team 17's decisions; because Team 21 didn't review the pull requests, Team 17 merged both (pod-k-shared #14 for 0.2.0 and #20 for 0.3.0) on November 22, 2026, with a merge note citing the November 1 email and stating that either change reopens if Team 21 objects.

**Intentional deviations and resolution plan:** None; the evaluation deployment at `c875f14` implements contract 0.3.0 as published.

## Q4.1 Test runner and execution instructions

**Base URL override:** Point the suite at https://team17-prod-7zneiwx4ba-uc.a.run.app (the base URL, no path prefix) and send "Authorization: Bearer <token>" on every request except GET /health. Our own tester takes any team's base URL through the CRA_BASE_URL environment variable or the --base-url option, with no code changes, and our deployed tester takes it as `target_url` in POST https://team17-prod-7zneiwx4ba-uc.a.run.app/tester/test/setup. │ **Response received:** GET /health → 200 `{"status": "ok"}`; an authenticated GET /tickets → 200 with a JSON array of tickets (captured November 22, 2026) │ **Conforms to spec:** yes

**Known deviations from the OpenAPI spec:** none (contract 0.3.0, as in Q3.2).

## Q4.2 Tests for new functionality

Every AC of the REQs completed in Phase 5 maps to a named test. All run through the common interface except where marked CI only.

AC-18 │ Requirement(s): REQ-17 │ Test(s): `acceptance/perf.py` (1,000 tickets, 200 sequential mixed requests across 11 operations, every status checked; fails on p95 > 1 s or any unexpected status); `tests/test_perf_script.py` (percentiles, mix, a fast 500 still fails); `tests/test_query_counts.py` (list and detail stay at a fixed number of queries at 1,000 tickets) │ Type: boundary (1,000 tickets), failure (unexpected status) │ Automated: yes (run against a deployment on demand, not in CI, because it loads 1,000 tickets)

AC-19 │ Requirement(s): REQ-18 │ Test(s): `scripts/restart_demo.sh` (create, triage, record, force a new revision, compare byte-for-byte) │ Type: success │ Automated: scripted; the spec requires a recorded demo ("Recorded demo by the owning team"), because a restart can't be triggered through the common interface. Alternative evidence: the video in Q1.1, plus the same script passing twice on the development deployment.

AC-13 │ Requirement(s): REQ-12 │ Test(s): `tests/test_malformed_requests.py` (664 generated malformed requests in CI against the in-process app) and `acceptance/malformed.py` against a deployment (683 on macOS; the generator draws different values per operating system, both cover the same 133 fault categories), generated with Schemathesis [8] │ Type: failure │ Automated: yes

AC-07 │ Requirement(s): REQ-06 │ Test(s): `acceptance/http_gap_cases.py`: `test_ac07_awareness_edit_recalculates_all_deadlines_and_records_audit`, `test_ac07_setting_fix_time_immediately_creates_final_deadline`, `test_ac07_rejected_edit_preserves_ticket_drafts_list_and_audit` │ Type: success, failure │ Automated: yes (now in the HTTP tester too)

Q7 (REQ-01), Q9 (REQ-08) │ Test(s): `tests/test_contract_030.py::TestSubmitFutureFixTime` (`test_later_than_now_is_422_and_stores_nothing`, `test_equal_to_or_before_now_is_accepted`), `::TestUnknownMemberStates` (`test_submit_accepts_and_echoes_unknown`, `test_unknown_mixed_or_repeated_is_400_on_member_states`), `::TestUnknownMemberStatesInReports`, `::test_update_422_lists_every_rule_problem` │ Type: failure (422), boundary (equal to now), success (`["unknown"]`) │ Automated: yes (CI only, through the API with Django's test client; kept out of the cross-team suite until Team 21 deploys 0.3.0)

Console lockout (LIM-12) and in-place saves (5.7) │ Test(s): `tests/test_console_lockout.py` (for example `test_the_fifth_failure_locks_with_the_generic_message`, `test_the_test_clock_has_no_effect`), `tests/test_console_forms.py` and `tests/test_console_reports.py` (saves return the updated page, refused saves change nothing) │ Type: success, failure │ Automated: yes (server tests), plus browser screenshots at 1280 and 390 px

**Oracles:** Every run starts with `POST /test/reset` and a fixed test clock, so results are deterministic, and as in earlier phases expected values come from the pod spec worked out by hand, never from our service's output: deadlines from Model D, required fields from Model C, status codes and their order from the OpenAPI contract, which our tester uses to validate every response. AC-18's oracle is the spec's own threshold (p95 ≤ 1 s) on latencies measured by the client, with a status check on every request so a fast error can't pass; AC-19 compares the raw responses before and after the restart byte-for-byte; AC-13's oracle is the contract itself (any 2xx or 5xx, an undocumented status, a non-problem+json body, or a changed row count fails).

## Q4.3 Regression and static checks

Every push and pull request runs our full CI pipeline in GitHub Actions, and nothing deploys unless it passes: in Phase 5, 13 runs on main all passed (6 more were cancelled because a newer merge superseded them), and the 3 failures on pull-request branches were fixed before merging. The pipeline runs the complete test suite (1,684 tests at `c875f14`) against PostgreSQL 18, which re-runs every earlier platform, unit and integration test and the whole portable acceptance suite (AC-01 to AC-17 plus the new AC-07 HTTP cases and the generated AC-13 run) in-process, so a change that breaks earlier behavior can't merge; the same acceptance cases run over HTTP against the deployments through our deployed tester. Every code change also gets an independent review by a teammate or a fresh AI session before it merges.

CI run: https://github.com/team17-ece30861/cra-service/actions/runs/45046366880

## Q4.4 Static checks

Our static checks are unchanged since Phase 3 except for one addition: CI still runs ruff (linting and formatting), a check for missing migrations, Django's system checks, and contract validation of every tester response, and Dependabot alerts and secret scanning with push protection are on; new this phase, Schemathesis [8] reads the OpenAPI file and generates requests from it in CI. We still don't use a type checker or pre-commit hooks. A failing check blocks merging and deploying.

CI run: https://github.com/team17-ece30861/cra-service/actions/runs/45046366880

## Q4.5 Test results against the deployed system

Run date/time: November 22, 2026, 12:13 to 12:20 PM Eastern (our deployed tester against the evaluation deployment) │ Version tested: `c875f14` │ Tests run: 241 │ Passed: 241 │ Failed: 0 │ Skipped: 0

Failures: none, all passed. Also against `c875f14` the same day: AC-18 p50 243 ms, p95 736 ms, max 1,750 ms (n = 200, 1,000 tickets; first request after the untimed warm-up 213 ms); AC-13 683 requests, 0 server errors, 0 contract mismatches, stored data unchanged; and our command-line run of the same suite from a team laptop, 1:33 to 1:48 PM Eastern, passed 240 of 241; its one error (`test_close_does_not_revalidate_locked_report_content`) is classified as test environment, not system: the laptop's TLS handshake timed out during that test's setup, no request reached the service (0 server errors logged), and the same test passed in the deployed tester's run above.

## Q5.1 Model updates

Model A: Ticket lifecycle (state machine) │ Changed: no │ What changed and why: Phase 5 added no states or transitions; the Phase 4 version matches the delivered service, including the failure paths (409 for a change to a closed ticket, re-triage rejected). │ Location: https://github.com/team17-ece30861/cra-service/tree/main/docs/models

Model B: Report status (state machine) │ Changed: no │ What changed and why: unchanged since Phase 4. │ Location: same

Model C: Required fields per draft (table) │ Changed: yes │ What changed and why: the early warning's member states may now be `["unknown"]`, which counts as filled in, because Art. 14(2)(a) [1] asks for them only "where applicable" (pod Q9). │ Location: https://github.com/team17-ece30861/pod-k-shared/blob/main/spec.md (Model C table, `member_states` row)

Model D: Deadline examples (table) │ Changed: no (wording) │ What changed and why: the examples are unchanged; the definition of the fix time now says "first corrective or mitigating measure" (Q8), which doesn't change any example. │ Location: pod-k-shared spec.md

Architecture and data flow (component diagram, Section 7.1) │ Changed: yes │ What changed and why: adds what Phase 5 delivered: compression in the middleware, the console's sign-in lockout (new `SignInFailure` table) and in-place saves, the deployed tester's one-run rule, heartbeat and cleanup, kept database connections, and the Cloud Monitoring alert that emails the team on any 5xx. Every element and arrow is labeled, with a legend. │ Location: https://github.com/team17-ece30861/cra-service/blob/main/docs/models/architecture.png

Information model: the tables in the diagram (Ticket, AuditEntry, ReportSubmission, FixedClock, SystemSession, TesterSession, SignInFailure) are defined in `core/models.py`, `tester/models.py` and `console/models.py`.

Design requirements and model coverage: our 44 design requirements and how each maps to tests are in https://github.com/team17-ece30861/cra-service/blob/e4e8e33cfadfd29a9e71137a94a37593258f6b5d/docs/model-coverage.md; our tester reported `coverage.model` 20 of 44 against our own system at `c875f14` (a requirement counts only when every scenario bound to it was evaluated).

## Q5.2 Model-implementation consistency

Our deployed tester now checks model consistency on every run against our own system: each of our 44 design requirements is bound to named test scenarios, and a requirement counts only when every scenario bound to it ran (20 of 44 at `c875f14`), while for the changed models a fresh AI session that hadn't written the code traced each changed element (the Model C `member_states` row and each new box in the architecture diagram) to the code and tests before merge. The divergence found this phase was in Model C, which required at least one Member State code in the early warning, stricter than Art. 14(2)(a) [1], which asks for them only "where applicable", so a manufacturer who didn't yet know the affected states couldn't record an on-time early warning. We corrected the model and the code together (contract 0.3.0, PR #111), because the model, not the regulation, was wrong. A grader can match it in the `member_states` row of Model C, in `tests/test_contract_030.py::TestUnknownMemberStates`, and on the evaluation deployment, where `POST /tickets` with `"member_states": ["unknown"]` returns 201 and echoes the value back.

## Q6.1 Cross-team test

[Q6.1 OUR SUITE vs TEAM 21: after 11 PM ET]

Team 21 tests → our service │ Date: November 22, 2026, 12:30 PM Eastern │ Run/passed: 17/17 │ Main problem and owner: none │ Coverage: code: not reported (our deployed service isn't instrumented for code coverage); component: not measured (the pod spec defines no component list); system: 17 of 19 acceptance criteria, one test each for AC-01 to AC-17, including 500 malformed requests for AC-13 with no server errors │ Note: Team 21 didn't run it this phase, so Team 17 ran Team 21's published tester (pod-k-shared `team21/tester`, version 0.4.2, unchanged since November 1) on our own machine, pointed at our evaluation deployment at `c875f14` with Team 17's own token

## Q6.2 Specification issues discovered

Issue: The final report deadline (REQ-04, `fix.available_at`): Art. 14(2)(c) [1] starts the 14-day clock when a corrective or mitigating measure is available, but the spec only said "fix". │ Effect: a team that recorded a workaround as something other than the fix would compute a final report due date later than the regulation allows; tests based on Model D couldn't tell the difference. │ Pod decision or plan: defined as the first corrective or mitigating measure in contract 0.3.0 (pod-k-shared #20, merged November 22, 2026; wording only, no example changes). Asked in our October 27 email; Team 21 didn't answer, so this is Team 17's decision, and it reopens if Team 21 objects.

## Q7.1 What changed and what remains incomplete

Changed since Phase 2:
- Deployed on Google Cloud Run with Neon PostgreSQL, per-client tokens, X-Actor, a 64 KB limit and contract-format errors in the agreed precedence (REQ-12, REQ-14; AC-02, AC-15); intake, triage, deadlines and updates (REQ-01 to REQ-04, REQ-06; AC-01, AC-03 to AC-05, AC-07, AC-14) in Phase 3.
- The full reporting workflow in Phase 4 (REQ-05, REQ-07 to REQ-11, REQ-15; AC-06, AC-08 to AC-12, AC-16) and the console.
- New in Phase 5: performance measured with 1,000 tickets (REQ-17; AC-18), persistence shown across a restart (REQ-18; AC-19), our own generated malformed-request run (REQ-12; AC-13), the Q7/Q8/Q9 contract changes (REQ-01, REQ-04, REQ-08), the server-error alert, the console's in-place saves and sign-in lockout, and the tester's model coverage, run lock, restart recovery and cleanup (REQ-16).

Remaining incomplete:
- Nothing from the pod's planned scope remains incomplete (REQ-01 to REQ-18 complete; AC-01 to AC-19 demonstrated).

## Q7.2 Known limitations and defects

This is the final phase, so no later fix is planned for any open item; each gives the workaround. Fixed in Phase 5 and no longer limitations: LIM-05 (contract 0.3.0 merged in the shared repository), LIM-06 (0.2.0 freeze merged), LIM-11 (test gaps closed by the AC-07 HTTP cases and AC-13), LIM-12 (console sign-in lockout), LIM-13 (tester cleanup).
- LIM-01 Shared state (REQ-16; `/test/reset`, `/test/clock`) │ Severity: medium │ All clients share one database and test clock, so a reset deletes everyone's data and two suites at once interfere. Workaround: one suite at a time (our deployed tester enforces this), finishing with a reset and clock release.
- LIM-02 Hosting performance (REQ-17) │ Severity: low │ Scale to zero means the first request after idle takes about 3 to 6 s; AC-18 passed warm (p95 736 ms), but single filtered list requests reached 1.75 s. Workaround: send GET /health and one authenticated read before timing.
- LIM-03 Spending cap (all operations) │ Severity: low │ A $10 cap stops the service until lifted by hand, and a stopped service sends no alert. Workaround: email Team 17.
- LIM-04 Final report clock (REQ-04; `fix.available_at`) │ Severity: low │ The system can't tell a fix from a workaround. Workaround: record the workaround's time if it came first (Q8).
- LIM-07 Empty lists in mixed updates (REQ-11; PATCH /tickets/{id}) │ Severity: low │ An update that changes a real field and also sends an empty list for a never-set list records that list in the audit entry, though no read shows a difference. Workaround: omit unset lists from updates.
- LIM-08 Tokens (REQ-14; all protected operations) │ Severity: medium │ No rate limiting; tokens are long-lived and rotated by hand. Workaround: tell us if a token may have leaked.
- LIM-09 Health check (GET /health) │ Severity: low │ Returns 200 even if the database is down, and HEAD needs a token. Workaround: use an authenticated GET /tickets.
- LIM-10 GET with a body (all GET operations) │ Severity: low │ Google's front end rejects it before it reaches the service, without problem+json. Workaround: don't send bodies on GET.

No test failed in Q4.5; the one error in the command-line run was a laptop-side network timeout, not a defect, so it adds no limitation.

## Q7.3 Adjustments to next phase milestone

Phase 5 is the last milestone in Phase 2, Section 6 (6.1 to 6.3 cover Phases 3 to 5), so there is no next milestone to adjust and nothing needs pod agreement; the final version is `c875f14`. Priority risks from Phase 2, Section 9.1:
- Risk 1 (our reading of the CRA): reduced. The two findings from our CRA review are now in the contract: early warnings can be sent with unknown member states, and the final report clock starts at the first corrective or mitigating measure [1, Art. 14(2)].
- Risk 2 (cross-team compatibility): [RISK 2 after tonight's run] Team 21's tester passed 17 of 17 against our final version.
- Hosting performance: closed. AC-18 passed on the evaluation deployment (p95 736 ms against the 1 s target) after kept connections and compression cut a simple read from about 190 ms to about 40 ms on the server.
- New risk, now realized and handled: pod responsiveness at the end of the course. Team 21 didn't review the contract PRs or answer the last open question, so Team 17 merged the agreed changes and recorded Q8 as its own decision; a podmate could still disagree after the deadline.

## Q8.1 Actual GenAI use

Each teammate answers for themselves in the submitted document.

## Q9 References

[1] European Parliament and Council of the European Union. "Regulation (EU) 2024/2847 (Cyber Resilience Act)." October 23, 2024. https://eur-lex.europa.eu/eli/reg/2024/2847/oj. Accessed: 2026-11-22.

[2] Google Cloud. "Cloud Run documentation." https://docs.cloud.google.com/run/docs. Accessed: 2026-11-22.

[3] Neon. "Neon documentation." https://neon.com/docs/introduction. Accessed: 2026-11-22.

[4] Django Software Foundation. "Django documentation." Version 5.2. https://docs.djangoproject.com/en/5.2/. Accessed: 2026-11-22.

[5] Django Ninja. "Django Ninja." Version 1.8. https://django-ninja.dev/. Accessed: 2026-11-22.

[6] Google Cloud. "Secret Manager documentation." https://docs.cloud.google.com/secret-manager/docs. Accessed: 2026-11-22.

[7] Google Cloud. "Cloud Monitoring: alerting overview." https://docs.cloud.google.com/monitoring/alerts. Accessed: 2026-11-22.

[8] Schemathesis. "Schemathesis documentation." Version 4.33. https://schemathesis.readthedocs.io/. Accessed: 2026-11-22.
