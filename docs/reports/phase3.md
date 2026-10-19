# Phase 3 report: Team 17's final answers

Final text for each question, as agreed with Quincy and pasted into the team's Phase 3
draft. Kept here so the Phase 4 report can build on it. Evidence for each claim is in
[`docs/phase3.md`](../phase3.md). Citation numbers follow the report's reference list
([1] is the Cyber Resilience Act).

## Q1.1 Increment description

**Delivered capability:** Through the common HTTPS interface, a client can now submit a vulnerability report as a ticket, triage it as actively exploited (with an awareness time and a reason) or close it as not reportable, and read back the exact Article 14 deadlines with a live status for the early warning (24 hours), the vulnerability notification (72 hours), and the final report (14 days after a fix is available) [1, Art. 14(1)-(2)]. Tickets can also be updated, which recalculates the deadlines immediately, and every successful change is recorded in a per-ticket audit log. **Users/stakeholders:** the manufacturer's product security and compliance staff, who no longer track deadlines informally and risk missing them for reports that arrive outside working hours; reporters, whose contact details appear only in the single-ticket view; and Team 21 and the course staff, who test the service through its reset and fixed-clock controls. **Regulatory provision(s):** the reporting obligations for actively exploited vulnerabilities [1, Art. 14(1)-(2)(a)-(c)], the contact point for receiving vulnerability reports [1, Art. 13(17); Annex I, Part II(6)], and the definition of an actively exploited vulnerability [1, Art. 3(42)]. The increment is deployed on Google Cloud Run [2] with a managed Neon PostgreSQL database [3], and our acceptance suite passed 55 of 55 tests against the evaluation deployment on October 17, 2026; Team 21's run against it is still pending.

REQ-01 - Intake │ Status: complete │ Demonstrated by: AC-01, AC-02
REQ-02 - Ticket marked as reportable │ Status: complete │ Demonstrated by: AC-03, AC-04
REQ-03 - Ticket marked as not reportable │ Status: complete │ Demonstrated by: AC-05
REQ-04 - Deadline computation │ Status: complete │ Demonstrated by: AC-03
REQ-05 - Obligation status │ Status: partial │ Demonstrated by: AC-03, AC-06 (unsubmitted statuses only) │ Missing: the submitted and submitted_late statuses, which depend on submission recording (Phase 4)
REQ-06 - Updates and recalculation │ Status: complete │ Demonstrated by: AC-07
REQ-09 - Closure │ Status: partial │ Demonstrated by: AC-05 │ Missing: closing a reportable ticket after all three reports are submitted (AC-10, Phase 4)
REQ-10 - Listing │ Status: partial │ Demonstrated by: AC-17 (unfiltered list) │ Missing: filtering by state and report status (AC-11, Phase 4)
REQ-11 - Audit log │ Status: partial │ Demonstrated by: integration tests (one entry per successful change, none for failed requests) │ Missing: the full scripted lifecycle in AC-12, which needs the Phase 4 actions
REQ-12 - Error handling │ Status: partial │ Demonstrated by: AC-02, AC-04, AC-14 │ Missing: 500 generated malformed requests (AC-13, Phase 4)
REQ-13 - Time format │ Status: complete │ Demonstrated by: AC-01, AC-14
REQ-14 - Authentication and HTTPS │ Status: complete │ Demonstrated by: AC-15
REQ-15 - Reporter confidentiality │ Status: partial │ Demonstrated by: AC-16 (single-ticket view, lists, and audit log only) │ Missing: report drafts and error responses, which arrive in Phase 4
REQ-16 - Test controls │ Status: complete │ Demonstrated by: AC-17
REQ-18 - Persistence │ Status: complete │ Demonstrated by: a ticket and its audit log read back unchanged after a new deployment replaced the running service (October 17, 2026); the recorded demonstration in AC-19 is planned for Phase 5

**To revisit before submitting:** if Team 21 runs their suite against us first, update the last sentence of the narrative.

## Q1.2 Comparison with the Phase 2 plan

We delivered the Phase 3 capability planned in Phase 2, Section 6.1: a deployed HTTPS service with authentication, test controls, ticket submission, triage, and deadline calculation (REQ-01 to REQ-04, REQ-12 to REQ-14, REQ-16), together with the planned automated validation (AC-01 to AC-05, AC-14, AC-15, and AC-17, with every response checked against the shared OpenAPI schemas [4]), our base URL in the shared pod repository, and a team CI pipeline. Three planned items are not yet finished: the shared OpenAPI file is still a draft rather than frozen for the Phase 3 operations, the shared test file covering all eight Model D examples has been submitted to the pod's shared repository but not yet cross-checked by Team 21, and the pod has not yet run the shared suite against both deployments, since so far only our own suites have passed against our service. We also delivered part of the Phase 4 scope early: ticket updates with immediate deadline recalculation (REQ-06), per-ticket audit log entries, an ordered ticket list, and reporter confidentiality for the operations built so far. There were no instructor-required scope changes, and the pod has not changed or reduced the shared scope.

**To revisit before submitting:** update sentence 2 if the contract is frozen (Ann, 3.9), Team 21 approves the shared test file (pod-k-shared #8), or the cross-team runs happen (3.8).

## Q2.1 Deployed web service

Our service runs on Google Cloud Run [2] in the us-central1 region as a Docker container (Python 3.12, Django with Django Ninja [5], served by gunicorn), backed by a managed Neon PostgreSQL database [3], with secrets such as database credentials and per-client API tokens stored in Google Secret Manager [6]. Every release is built as a container image labeled with the exact Git commit it came from, so any running version maps back to a specific commit; changes merged to our main branch are tested in CI and deployed automatically to a separate development instance used only by our team, while the evaluation deployment is updated only through a manual release step that reruns the tests, applies database migrations, deploys, and checks the health endpoint. The service is reachable at all times but scales to zero when idle, so the first request after a quiet period takes about 3 to 6 seconds while an instance starts (plus about 1.5 seconds for the first database read), and it would become unavailable only if its $10 spending cap were reached, which stops it until we lift the cap manually. There is no rate limit, but it runs as a single instance that handles two requests at a time with a 30-second timeout and a 64 KB request size limit, all clients share one database and one test clock so test runs should be coordinated, and each team and the course staff have their own access token, which must be kept private.

**Choices made with Quincy:** no deployed version or hash named (the course staff can't see the repo, and it will change); "labeled with the exact Git commit" rather than "Git tags" (we don't create Git tags); `/test/reset` deliberately not mentioned (whether to keep or change it is a later discussion; it's required by REQ-16, so changing it needs Team 21).

## Q2.2 Registry and team documentation

Registry entry: Cross-team testing endpoint registry (Endpoint_Registry Google Sheet), Pod K, Team 17 row │ Updated on: October 17, 2026
Team documentation: https://github.com/team17-ece30861/pod-k-shared/blob/main/team17/SYSTEM.md │ Updated on: October 17, 2026

**Notes:** dates in this report use US Eastern time, the team's local date. Logs, test runs, and `docs/phase3.md` record UTC, which was already October 18 for the evening runs. The registry row holds the system URL, the tester (`pod-k-shared/team17/tester`), the spec (`pod-k-shared/spec.md`), and access notes, including that course staff get their token from Quincy.

## Q2.3 Operational experience supported by observability evidence

Our Phase 2 plan held up in practice: the service runs on Google Cloud Run with a persistent Neon PostgreSQL database and separate development and evaluation deployments, and tickets and their audit entries survive restarts and redeploys, changing only through the API or the pod's test reset control, which clears all tickets and audit entries so cross-team tests start from a known state. Secrets live in Google Secret Manager and are injected as environment variables at deploy time, with one API token per client (our team, Team 21, and the course staff) so each can be replaced independently, while GitHub Actions deploys through Workload Identity Federation [7] without stored keys and database migrations run as a separate job before each release. To detect failures, the access log records every request with the name of the client whose token matched (never the token itself), the application logs each rejected request and a stack trace without request data for any server error, and Cloud Run's request log records each request's status code and latency; request bodies are never logged. In practice, failures have been caught by CI on every change, the health check after each deployment, our acceptance runs, and reviewing these logs, but unlike our plan we have not yet set up automated alerts beyond a budget alert, and we plan to add an alert on server errors in Phase 4. Over the last day, the evaluation deployment logged 0 server errors and 46 client errors, 43 from our acceptance suite's deliberately invalid requests and 3 from a browser opening the service without a token.

Excerpt from the evaluation deployment's logs (October 17, 2026, 8:51 PM Eastern; times shown in UTC):

```
# Access log: the client is identified by name, never by token
169.254.169.126 - team17 [18/Oct/2026:00:51:33 +0000] "POST /tickets HTTP/1.1" 201 885 "-" "Python-urllib/3.12"
169.254.169.126 - team17 [18/Oct/2026:00:51:34 +0000] "GET /tickets/b30921b2-e21e-447e-82dc-25d97ae32958 HTTP/1.1" 200 968 "-" "Python-urllib/3.12"
# Application warning for a rejected request (path only, no request body)
2026-10-18T00:51:35Z  Bad Request: /tickets
# Cloud Run request log: method, status, latency
2026-10-18T00:51:33Z  POST  201  0.310 s  /tickets
```

**Evidence checked 2026-10-17 (Eastern):** Cloud Monitoring has 0 alert policies and 0 uptime checks; the 46 4xx were grouped by minute and user agent (43 from the acceptance run at 00:51–00:52 UTC, 3 browser 401s at 03:32 UTC). Choices with Quincy: the reset endpoint isn't named; the alerting gap is reported, with the fix planned for Phase 4.

## Q3.1 Operation status

GET /health │ Requirement(s): none │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (none defined)
POST /tickets │ Requirement(s): REQ-01, REQ-12, REQ-13, REQ-14 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (400, 401, 413)
GET /tickets │ Requirement(s): REQ-10, REQ-15 │ Implemented: partial │ Success responses conform: no; the list is ordered nearest deadline first without reporter details, but the state and obligation_status filters are ignored │ Error responses conform: no; 401 conforms, but invalid filter values return 200 instead of 400
GET /tickets/{id} │ Requirement(s): REQ-04, REQ-05 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (401, 404)
PATCH /tickets/{id} │ Requirement(s): REQ-04, REQ-06 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (400, 401, 404, 409, 413, 422)
POST /tickets/{id}/triage │ Requirement(s): REQ-02, REQ-03 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (400, 401, 404, 409, 422)
GET /tickets/{id}/reports/{type} │ Requirement(s): REQ-07, REQ-15 │ Implemented: no (Phase 4) │ Success responses conform: no; returns 404 for every type │ Error responses conform: partial; 401 conforms, 409 not implemented
POST /tickets/{id}/reports/{type}/submission │ Requirement(s): REQ-05, REQ-08 │ Implemented: no (Phase 4) │ Success responses conform: no; returns 404 │ Error responses conform: partial; 401 conforms, 400/409/422 not implemented
POST /tickets/{id}/close │ Requirement(s): REQ-09 │ Implemented: no (Phase 4) │ Success responses conform: no; returns 404 │ Error responses conform: partial; 401 conforms, 400/409 not implemented
GET /tickets/{id}/audit │ Requirement(s): REQ-11 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (401, 404, 405)
POST /test/reset │ Requirement(s): REQ-16 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (401)
GET /test/clock │ Requirement(s): REQ-16 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (401)
PUT /test/clock │ Requirement(s): REQ-16 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (400, 401)
DELETE /test/clock │ Requirement(s): REQ-16 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (401)

Integration: The new ticket operations are a router added to our existing Django Ninja API, backed by two new database tables (tickets and their audit entries) and pure domain functions for triage, deadlines, and statuses, while the platform layer built earlier is unchanged. A request passes through the platform middleware first (token check, body-size limit, and a database transaction), then the ticket route looks up and locks the ticket (404), checks the X-Actor header and the request body (400), and calls the domain rules with the service clock (409 for state conflicts, 422 for rule violations). On success the route saves the ticket and exactly one audit entry in the same transaction and builds the response from stored fields plus deadlines and statuses derived at read time; any error returns problem+json [8] and rolls the transaction back, so a failed request changes nothing.

**Evidence:** conformance for implemented operations comes from the acceptance suite, which validates every response against `openapi.yaml` (55/55 on the evaluation deployment), plus local integration tests and the manual AC-07 run. The unbuilt operations and list filters were probed on a local server on 2026-10-17 (404 problem+json; 401 without a token; invalid filters return 200). `/test/reset` is listed because the question asks for every contract operation (Quincy's call). Phases 4 and 5 ask for this table again; plan task 4.T5 makes the runner print it.

## Q3.2 Contract changes and pod communication

Contract version at delivery: 0.1.0-draft (an OpenAPI 3.1 translation of Phase 2, Section 5.1)
Changes since Phase 2: None to the contract's content. Team 17 translated Section 5.1 into an OpenAPI file on October 4 so both teams can check responses against it automatically, and published it in the pod's shared repository on October 17, notifying Team 21 by email; the formal freeze of the Phase 3 operations is pending Team 21's review.
Pod agreement: The Phase 2 specification was agreed asynchronously by email and finalized on September 25, 2026; no changes have been proposed or agreed since.
Intentional deviations and resolution plan: None. Known gaps, both scheduled for Phase 4: the report draft, submission, and close operations are not built yet, and GET /tickets ignores its filters (an invalid filter value returns 200 instead of 400). We are also still evaluating four interpretation questions where the contract is silent; until they are settled, our service's current behavior in each case is documented in our public testing guide.

**Notes:** `openapi.yaml` has had one commit (2026-10-04, `aadddf1`), and the `pod-k-shared` copy is byte-identical. The pod communicates by email. It's unknown whether Team 21 reviewed the OpenAPI file before it was published, so the answer doesn't claim they agreed to it. **To revisit before submitting:** if Ann completes the freeze (3.9), update the version and the "Changes" line. The four questions are plan Q1, Q7, Q8, and Q9; Quincy expects they may not be settled, so the answer commits only to evaluating them.

## Q4.1 Test runner and execution instructions

Base URL override: Point the suite at https://team17-prod-7zneiwx4ba-uc.a.run.app (the base URL, with no path prefix) and send "Authorization: Bearer <token>" on every request except GET /health; our own tester takes any team's base URL the same way, through the CRA_BASE_URL environment variable or the --base-url option, with no code changes. │ Response received: GET https://team17-prod-7zneiwx4ba-uc.a.run.app/health returned 200 with body {"status": "ok"} (October 18, 2026); a protected route without a token returned 401 with {"title": "Unauthorized", "status": 401}. │ Conforms to spec: yes; our acceptance suite checks every response against the OpenAPI spec and passed 55 of 55 tests against this deployment.
Known deviations from the OpenAPI spec: GET /tickets ignores the state and obligation_status filters, and an invalid filter value returns 200 instead of 400; the report draft, submission, and close operations are not built yet and return 404. Both are scheduled for Phase 4.

**Evidence:** live check 2026-10-18 04:05 UTC (00:05 Eastern): `/health` returned 200 `application/json` `{"status": "ok"}` in 0.30 s; `GET /tickets` without a token returned 401 problem+json. The deviations match Q3.1 and Q3.2.

## Q4.2 Tests for new functionality

AC-01 │ Requirement(s): REQ-01, REQ-13 │ Test(s): test_ac01_intake_has_unique_ids_and_fixed_receipt_time │ Type: success │ Automated: yes
AC-02 │ Requirement(s): REQ-01, REQ-12 │ Test(s): test_ac02_invalid_intake_preserves_ticket_count (missing title, unknown source, system-set field), test_ac02_malformed_intake_preserves_ticket_count (invalid JSON, body over 64 KB) │ Type: failure │ Automated: yes
AC-03 │ Requirement(s): REQ-02, REQ-04 │ Test(s): test_ac03_model_d_exact_deadlines_and_statuses (Model D E1 to E5), test_model_d_exact_published_deadlines, test_model_d_exact_published_statuses, deadline unit tests (year boundary, leap day, daylight-saving changes) │ Type: success, boundary │ Automated: yes
AC-04 │ Requirement(s): REQ-02 │ Test(s): test_ac04_rejected_triage_preserves_ticket (missing awareness time, future awareness time as in E8, missing reason), test_ac04_retriage_is_conflict_and_changes_nothing, triage unit tests │ Type: failure, boundary │ Automated: yes
AC-05 │ Requirement(s): REQ-03, REQ-09 │ Test(s): test_ac05_closed_ticket_remains_readable_and_rejects_changes (both non-reportable decisions) │ Type: success, failure │ Automated: yes
AC-06 (unsubmitted statuses only) │ Requirement(s): REQ-05 │ Test(s): test_initial_statuses_recalculate_at_exact_deadline (E6), status unit tests │ Type: boundary │ Automated: yes; submitted and submitted_late arrive with Phase 4
AC-07 │ Requirement(s): REQ-06 │ Test(s): test_update_merges_nested_fields_and_recalculates, test_awareness_change_needs_reason_and_reportable_state, test_sent_future_fix_time_is_rejected_without_changes, test_failed_update_preserves_data_and_audit │ Type: success, failure │ Automated: yes, in our CI integration tests (also checked by hand on our development deployment; not yet in the HTTP suite)
AC-12 (partial) │ Requirement(s): REQ-11 │ Test(s): test_audit_has_one_entry_per_success_and_no_reporter, test_failed_update_preserves_data_and_audit, test_concurrent_triage_has_one_success_and_one_audit_entry │ Type: success, failure │ Automated: yes; the full scripted lifecycle needs the Phase 4 operations
AC-14 │ Requirement(s): REQ-13 │ Test(s): test_ac14_timestamps_are_normalized (E7 offset, fractional seconds), test_ac14_bad_timestamp_leaves_ticket_unchanged (bad format, missing seconds, missing offset) │ Type: success, failure │ Automated: yes
AC-15 │ Requirement(s): REQ-14 │ Test(s): test_ac15_every_protected_operation_rejects_unauthorized_requests (every operation, no token and wrong token), test_ac15_health_is_public, test_ac15_missing_actor_changes_nothing, test_ac15_plain_http_is_refused_or_redirected_to_https │ Type: failure │ Automated: yes
AC-16 (partial) │ Requirement(s): REQ-15 │ Test(s): reporter checks in test_ac01_intake_has_unique_ids_and_fixed_receipt_time and in every create and list call, test_audit_has_one_entry_per_success_and_no_reporter │ Type: success │ Automated: yes; drafts and error bodies arrive with Phase 4
AC-17 │ Requirement(s): REQ-16 │ Test(s): test_ac17_reset_deletes_tickets, test_ac17_clock_stays_fixed_and_controls_receipt, test_invalid_clock_update_preserves_clock │ Type: success, failure │ Automated: yes
AC-19 (early check) │ Requirement(s): REQ-18 │ Test(s): restart check on our development deployment (ticket and audit log read back unchanged after a new revision) │ Type: success │ Automated: no; it needs a service restart only our team can trigger, and the recorded demonstration is planned for Phase 5

Oracles: Every expected output comes from the pod specification, never from running our code: deadlines and statuses are the Phase 2 Model D examples and Model B rules, which we worked out by hand and checked again independently (for example, the leap-day and daylight-saving cases), and status codes and error formats come from the shared OpenAPI contract. Every HTTP response is also validated automatically against that contract, using a validator whose own tests confirm it rejects malformed responses. We trust these oracles because they were fixed before the code was written, the same cases pass both in CI and against the deployed service, and the Model D cases have been submitted to Team 21 for independent checking in the pod's shared test file.

**Notes:** test names checked against `acceptance/cases.py`, `acceptance/test_phase3.py`, `tests/test_phase3_api.py`, and the unit test files on 2026-10-18. Known small gap, not in the answer: the audit log's 404 and 405 have no dedicated tests (both were checked by hand); see plan task 4.T6.

## Q4.3 Regression and static checks

Every push and pull request runs our full CI pipeline in GitHub Actions, and nothing is deployed unless it passes: lint and formatting checks (ruff), a check that every database model change has a migration, Django's system checks, and the complete test suite against a real PostgreSQL 18 database, which re-runs all earlier platform, unit, and integration tests together with the Phase 3 acceptance cases (518 tests in the run linked below). The acceptance cases validate every response against the shared OpenAPI contract, so each later phase is checked against the same contract tests, and the same cases are re-run over HTTPS against our development deployment before each release and against the evaluation deployment after it. When we find a bug, we first write a regression test that fails and only then fix it, as we did this phase for a bug where every update re-checked a stored fix time. Across all 45 CI runs on our main branch so far, none has failed, and the evaluation deployment is updated only through a manual release step that re-runs the full test suite first.

CI run: https://github.com/team17-ece30861/cra-service/actions/runs/39096210486

**Notes:** `cra-service` was made public on 2026-10-18, so graders can open the CI link. The repository history was scanned on 2026-10-18 before any visibility change: no secrets in any commit, branch, or CI log. Repository settings (Quincy, 2026-10-18): Actions limited to our organization, GitHub's own actions, and google-github-actions/auth and setup-gcloud; fork pull request workflows need approval; `main` requires a pull request.

## Q4.4 Static checks

Our CI runs static checks on every push and pull request: ruff for linting and formatting, a check that no database migrations are missing, and Django's system checks; contract validation runs in the same pipeline, where every response in the acceptance tests is checked against the shared OpenAPI contract by a validator that has its own tests, and GitHub's Dependabot alerts flag known-vulnerable dependencies. A failing check blocks both merging and deployment, because our main branch only accepts pull requests whose CI tests pass, and both the automatic development deployment and the manual evaluation release run only after the full suite passes. These checks are new this phase (Phase 2 only planned them); we do not yet use a type checker or pre-commit hooks, and secret scanning with push protection was enabled when the repository became public.

CI run: https://github.com/team17-ece30861/cra-service/actions/runs/39097458488

**Evidence (2026-10-18, via the GitHub API):** ruleset `main` is active, with rules for deletion, non-fast-forward, pull request, and the required status check `test / test`. Dependabot alerts are on and Dependabot security updates are off. Secret scanning and push protection are on, with 0 alerts on the full history. There's no pre-commit config, type checker, or dependabot.yml.

## Q4.5 Test results against the deployed system

Run date/time: October 17, 2026, 8:51–8:52 PM Eastern (00:51–00:52 UTC on October 18) │ Version tested: 262fedf │ Tests run: 55 │ Passed: 55 │ Failed: 0 │ Skipped: 0

Failures: none. The full acceptance suite ran over HTTPS against our evaluation deployment and passed every test, including the plain-HTTP check that only runs against a deployment; every response was also validated against the shared OpenAPI contract.

**Notes:** the evaluation deployment still runs `262fedf`; every later commit is docs only. The report is a Gradescope form, so "the version on the cover page" likely means a header question; if it asks for a version, use `262fedf`.

## Q5.1 Model updates

Model A: Ticket lifecycle (state machine) │ Changed: yes │ What changed and why: Redrawn to show what was delivered: submitting a ticket, both triage outcomes, and updates are implemented, while recording report submissions and closing a reportable ticket as resolved are specified but arrive in Phase 4, so they appear dotted; updates are now listed inside each state instead of drawn as self-loops. │ Location: https://github.com/team17-ece30861/cra-service/blob/main/docs/models/model-a-ticket-lifecycle.png
Model B: Report status (state machine) │ Changed: yes │ What changed and why: The not_applicable, awaiting_fix, pending, and overdue statuses are delivered and recalculated on every read, while submitted and submitted_late depend on submission recording and arrive in Phase 4 (dotted); we also added a transition from awaiting_fix directly to overdue, which happens when a fix is recorded after its 14-day due time has already passed and was missing from the Phase 2 model. │ Location: https://github.com/team17-ece30861/cra-service/blob/main/docs/models/model-b-report-status.png
Model C: Required fields per draft (table) │ Changed: no │ What changed and why: Report drafts are not built yet (Phase 4); our review of the regulation found the early-warning required fields may be stricter than Article 14(2)(a) requires [1], which is still under evaluation. │ Location: Phase 2, Section 3.2 (unchanged); also https://github.com/team17-ece30861/pod-k-shared/blob/main/spec.md
Model D: Deadline examples (table) │ Changed: no │ What changed and why: The delivered service reproduces all eight examples exactly, as checked by the pod's shared test file. │ Location: Phase 2, Section 3.2 (unchanged); also https://github.com/team17-ece30861/pod-k-shared/blob/main/spec.md
Architecture and data flow (component diagram, Section 7.1) │ Changed: yes │ What changed and why: We removed the report draft generator and stored reports, which do not exist until Phase 4; audit logging turned out to be part of the ticket routes rather than a separate component; we added the platform middleware (token check, request-size limit, and one database transaction per write) and the service clock; and we named the actual technologies (Cloud Run, Django Ninja, Neon PostgreSQL), which Phase 2 left undecided. │ Location: https://github.com/team17-ece30861/cra-service/blob/main/docs/models/architecture.png

Updated diagrams: all models, with their sources and change notes, are at https://github.com/team17-ece30861/cra-service/tree/main/docs/models. In every diagram, solid elements are delivered and dashed or dotted elements are specified for Phase 4.

**Notes:** diagrams are linked rather than pasted (Quincy's choice). They were checked against the code and inspected as renders; see `docs/models/README.md`.

## Q5.2 Model-implementation consistency

We verified each updated model against the code rather than generating it: every state transition was traced to the domain functions that implement it (triage, deadlines, and statuses) and to the tests that exercise it, every component in the architecture diagram was matched to an actual module in the service, and anything specified but not yet built was drawn dotted rather than omitted or shown as existing. Model D is also checked automatically, because the acceptance suite and the pod's shared test file assert its exact deadlines and statuses against the deployed service, and every response is validated against the OpenAPI contract. One divergence was in Model B: the Phase 2 model only allowed awaiting_fix to become pending once a fix time is recorded, but the implementation correctly goes straight to overdue when the fix was recorded more than 14 days earlier, so we corrected the model. A divergence in the other direction was in the update rule (REQ-06): the code rejected any update whenever a previously stored fix time was later than the current time, even if the update did not touch it, so we corrected the code and added regression tests.

**Notes:** the code fix is cra-service PR #11. A teammate walkthrough isn't claimed, because none is confirmed; if Ann or Richard reviews the diagrams before submission, add "and reviewed by a teammate" to the first sentence.

## Q6.1 Cross-team test

Neither direction of the cross-team test was run before submission. Our side has been ready since October 17, 2026: our evaluation base URL is in the pod's shared repository and the class registry, Team 21 has its own access token, and our tester and testing guide are public. Team 21 published its system and tester URLs in the class registry on the evening of October 18; we confirmed at 9:00 PM Eastern that both respond and that the system's API documentation lists all 14 contract operations, but we had not yet received an access token, so we could not run our suite against it. Team 21's tester begins every run by calling two endpoints on the target system, POST /test/setup and GET /test/report, that are not part of our pod contract and that our service does not provide, so a run against our deployment would stop before any test; we will agree with Team 21 whether to add them to the pod contract and run both directions as the first item of our Phase 4 plan.

Our tests → Team 21 service │ Date: not run │ Run/passed: 0/0 │ Main problem and owner: no access token for our team yet (owner: Team 21 to send it; Team 17 will run our suite within one day of receiving it) │ Coverage: none yet. When run, our 55-test suite checks authentication on all 14 contract operations; success and error paths for submitting, reading, listing, and triaging tickets and for the test controls; all eight Model D examples; both triage outcomes in Model A; and the four unsubmitted statuses in Model B. Code coverage cannot be measured from outside another team's service.

Team 21 tests → our service │ Date: not run │ Run/passed: 0/0 │ Main problem and owner: Team 21's tester requires POST /test/setup and GET /test/report on the target, which are outside our pod contract and not implemented by our service (owner: both teams to agree on the interface; Team 17 to implement it if adopted) │ Coverage: none yet. When run, Team 21's tester checks one case each for AC-01 to AC-05, AC-14, AC-15, and AC-17 (8 of 19 acceptance criteria, including Model D example E3), and reads code coverage from the target's report endpoint.

**Notes:** Team 21's registry row was filled in on 2026-10-18 evening (Eastern); their tester and test source were pushed to `pod-k-shared` `team21/` at 2026-10-19 00:58 UTC. Read-only checks at 2026-10-19 ~01:00 UTC: `https://cra-phase3.onrender.com/health` 200 (33 s cold start), `https://cra-phase3-tester.onrender.com/health` 200 (22 s); the system's `/openapi.json` lists all 14 contract operations plus `/test/setup` and `/test/report`. No authenticated request was sent. Tester behavior and coverage come from reading `team21/tester/main.py` (not run). Our coverage claims come from `acceptance/cases.py`. Orbit's logs had no `team21` client requests as of 2026-10-19 00:42 UTC. The email date (October 18) is assumed.

## Q6.2 Specification issues discovered

Issue: Triage (POST /tickets/{id}/triage, REQ-03) — the contract does not say what happens when a not_actively_exploited or invalid decision includes an awareness time; we accept the request and ignore the time, but rejecting it with 400 or storing it are equally consistent with the contract. Related gaps we found: the contract lists no 422 for submitting a ticket with a future fix time, and a review against the regulation suggests the final-report clock should start at a corrective or mitigating measure [1, Art. 14(2)(c)] rather than only a fix, and that the early warning's required fields are stricter than Art. 14(2)(a) requires [1]. │ Effect: These cases are where two independent implementations are most likely to diverge, so a cross-team test of them could fail on either service without either team having a bug; so far they show up only in our own design and testing, because cross-team runs have not happened yet. │ Pod decision or plan: No pod decision yet. Our current behavior in each case is documented in our public testing guide, and these questions will be discussed with Team 21 as cross-team testing continues.

**To revisit before submitting:** if the cross-team runs happen first, update "cross-team runs have not happened yet", and add any mismatch they find.

## Q7.1 What changed and what remains incomplete

Changed since Phase 2:
- The system went from design to a deployed service on Google Cloud Run with a Neon PostgreSQL database, with per-client bearer tokens, the X-Actor check, a 64 KB request limit, and contract-format errors in the agreed precedence order (REQ-12, REQ-14; AC-02, AC-15).
- Ticket intake, triage as reportable or not reportable, and exact Article 14 deadlines with live statuses for unsubmitted reports are delivered and pass on the deployed service (REQ-01 to REQ-05; AC-01, AC-03 to AC-05, AC-14, and the AC-06 boundary case).
- Several Phase 4 items arrived early: ticket updates with deadline recalculation, per-ticket audit entries, an ordered ticket list, and reporter details limited to the single-ticket view (REQ-06, REQ-10, REQ-11, REQ-15; AC-07, and parts of AC-12 and AC-16).
- Test controls (data reset and a fixed clock shared across all workers) support repeatable cross-team testing, and stored data survives a redeployment (REQ-16, REQ-18; AC-17).
- Testing infrastructure now exists: an acceptance suite that validates every response against the OpenAPI contract, CI that blocks merging and deployment on any failure, and a public pod repository with the specification, our testing guide, our tester, and a shared Model D test file.

Remaining incomplete:
- Report drafts with missing-field checks (including the user advisory), and recording report submissions with locked content and the submitted and submitted_late statuses that depend on it (REQ-05, REQ-07, REQ-08; AC-06, AC-08, AC-09).
- Closing a reportable ticket as resolved, and filtering the ticket list by state and report status (REQ-09, REQ-10; AC-10, AC-11).
- The full audit-log lifecycle, reporter confidentiality in drafts and error bodies, and testing with 500 or more generated malformed requests (REQ-11, REQ-12, REQ-15; AC-12, AC-13, AC-16).
- The performance target with 1,000 tickets and the recorded restart demonstration (REQ-17, REQ-18; AC-18, AC-19).
- Phase 3 pod items planned in Phase 2, Section 6.1: freezing the contract for the Phase 3 operations, Team 21's check of the shared Model D test file, and the two-way cross-team test runs.

**To revisit before submitting:** update the last "Remaining" bullet for any Phase 3 pod item that gets done (contract freeze, test-file approval, cross-team runs).

## Q7.2 Known limitations and defects

LIM-01 │ The report draft, submission, and close operations are not built yet and return 404 │ Affects: REQ-07, REQ-08, REQ-09; GET /tickets/{id}/reports/{type}, POST /tickets/{id}/reports/{type}/submission, POST /tickets/{id}/close │ Severity: medium (planned for Phase 4) │ Workaround for podmates: skip those tests until our status chart marks them live │ Target phase: 4
LIM-02 │ GET /tickets ignores the state and obligation_status filters, and an invalid filter value returns 200 instead of 400 │ Affects: REQ-10, REQ-12; GET /tickets │ Severity: medium │ Workaround for podmates: filter the returned list on the client side, and don't assert a 400 for bad filter values yet │ Target phase: 4
LIM-03 │ All clients share one database and one test clock, so a test reset deletes everyone's data and two suites running at once interfere │ Affects: REQ-16; all operations │ Severity: medium │ Workaround for podmates: run one suite at a time, and finish by resetting and releasing the clock │ Target phase: none planned (required by the shared test design)
LIM-04 │ The service scales to zero: the first request after idle takes about 3–6 seconds, plus about 1.5 seconds for the first database read; it runs one instance handling two requests at a time, with a 30-second timeout, and the 1-second performance target with 1,000 tickets has not been measured │ Affects: REQ-17; all operations │ Severity: medium │ Workaround for podmates: send GET /health and one authenticated read before timing anything, use timeouts of at least 30 seconds, and send requests one at a time │ Target phase: 5
LIM-05 │ A $10 spending cap stops the service until we lift it manually, and there is no automated alert for server errors or outages yet │ Affects: availability of all operations │ Severity: medium │ Workaround for podmates: if the service stops responding, email Team 17 │ Target phase: 4 (alerting)
LIM-06 │ The final-report deadline starts only from the recorded fix time, while the CRA starts it when any corrective or mitigating measure is available [1, Art. 14(2)(c)], so a workaround released before the fix can leave our due time later than the regulation requires │ Affects: REQ-04; final report deadline │ Severity: medium │ Workaround for podmates: record the time of the first mitigating measure as the fix time │ Target phase: 4 (pod decision)
LIM-07 │ Where the contract is silent, our behavior may differ from Team 21's: a not_actively_exploited or invalid triage that includes an awareness time is accepted and the time ignored, and a ticket submitted with a future fix time is accepted │ Affects: REQ-03, REQ-06; POST /tickets/{id}/triage, POST /tickets │ Severity: low │ Workaround for podmates: see the gray-areas section of our testing guide, and don't assert either behavior until the pod agrees │ Target phase: 4
LIM-08 │ No rate limiting, and bearer tokens are long-lived and rotated only by hand │ Affects: REQ-14; all operations │ Severity: low │ Workaround for podmates: keep your token private and tell us if it may have leaked, so we can replace it │ Target phase: 5
LIM-09 │ GET /health returns 200 even if the database is unreachable, and HEAD /health requires a token │ Affects: GET /health │ Severity: low │ Workaround for podmates: use an authenticated GET /tickets to check that the service is fully working, and GET (not HEAD) for health checks │ Target phase: 5
LIM-10 │ Google Cloud Run's front end rejects any GET request that has a body before it reaches our service, returning a dropped connection or an HTML 400 instead of our problem+json error │ Affects: REQ-12; all GET operations │ Severity: low │ Workaround for podmates: don't send request bodies with GET │ Target phase: none planned (hosting platform behavior)
LIM-11 │ Test gaps: the audit log's 404 and 405 responses and the AC-07 update cases are checked by our integration tests or by hand, but not yet by the HTTP acceptance suite; no tests are currently failing │ Affects: REQ-06, REQ-11 │ Severity: low │ Workaround for podmates: none needed │ Target phase: 4

**Notes:** every item was verified on 2026-10-17 or 18, or is documented in `pod-k-shared/team17/TESTING.md`. Rate limiting (LIM-08) and a database-aware health check (LIM-09) aren't plan tasks yet; add them when Phase 5 is planned.

## Q7.3 Adjustments to next phase milestone

The Phase 4 milestone in Phase 2, Section 6.2 still holds, and its scope is lighter than planned, because ticket updates with deadline recalculation (REQ-06) and parts of listing, the audit log, and reporter confidentiality (REQ-10, REQ-11, REQ-15) were delivered early in Phase 3. The main sequencing change is that Phase 4 will start by finishing the Phase 3 pod items that are still open (freezing the contract for the Phase 3 operations, Team 21's check of the shared Model D test file, and the first two-way cross-team runs) before the new reporting workflow, since every later cross-team test depends on them; this is a scheduling change within our team and does not change the shared scope. We are also adding work the plan did not list: automated alerting for server errors, automated tests for the remaining audit-log error paths, and a test report that generates the operation-status table directly.

Priority risks from Phase 2, Section 9.1:
- Reduced: Risk 1 (our reading of awareness time, fix availability, the 14-day final report, and its required contents might not match the CRA). We reviewed the deadline and required-field rules against the official text of Article 14: the deadlines and required report contents match Article 14(2) [1], and the review found two places where our specification may be stricter or later than the regulation.
- Remains: Risk 2 (cross-team compatibility). Our side is ready, with a public tester, testing guide, and shared test file, but no cross-team run has happened yet in either direction, so compatibility is still unproven.
- New: Hosting performance. The service scales to zero, so the first request after idle takes several seconds, and it runs as a single instance; this could threaten the Phase 5 target of 95% of requests within 1 second with 1,000 tickets (REQ-17), so we will measure it early in Phase 4 rather than waiting for Phase 5.
- New: Team capacity. Phase 4 concentrates most of the new API work on one owner; we will agree on the interfaces between the domain rules and the API early, so that both can be built in parallel.

**Decided with Quincy:** keep "measure it early in Phase 4" (plan task 4.P5) and the neutral team-capacity risk; Quincy cut the spec-questions sentence and the cross-team-scheduling and AI-generated-work risks. **To revisit:** if cross-team runs happen before submitting, update the Risk 2 bullet.

## Q9 References

[1] European Parliament and Council of the European Union. "Regulation (EU) 2024/2847 (Cyber Resilience Act)." October 23, 2024. https://eur-lex.europa.eu/eli/reg/2024/2847/oj. Accessed: 2026-10-18.
[2] Google Cloud. "Cloud Run documentation." https://docs.cloud.google.com/run/docs. Accessed: 2026-10-18.
[3] Neon. "Neon documentation." https://neon.com/docs/introduction. Accessed: 2026-10-18.
[4] OpenAPI Initiative. "OpenAPI Specification v3.1.0." February 15, 2021. https://spec.openapis.org/oas/v3.1.0. Accessed: 2026-10-18.
[5] Django Ninja. "Django Ninja." Version 1.x. https://django-ninja.dev/. Accessed: 2026-10-18.
[6] Google Cloud. "Secret Manager documentation." https://docs.cloud.google.com/secret-manager/docs. Accessed: 2026-10-18.
[7] Google Cloud. "Workload Identity Federation." Identity and Access Management (IAM) documentation. https://docs.cloud.google.com/iam/docs/workload-identity-federation. Accessed: 2026-10-18.
[8] Internet Engineering Task Force (IETF). "RFC 9457: Problem Details for HTTP APIs." July 2023. https://www.rfc-editor.org/rfc/rfc9457. Accessed: 2026-10-18.

**Notes:** numbered by first citation in this report (Q1.1 → [1], [2], [3]; Q1.2 → [4]; Q2.1 → [5], [6]; Q2.3 → [7]; Q3.1 → [8]). Every URL was checked on 2026-10-18 and loads; the three Google URLs are the final addresses after redirects. Phase 2's FastAPI, SQLite, and SQLAlchemy references were dropped, since we didn't use them.
