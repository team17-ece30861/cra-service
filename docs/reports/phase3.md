# Phase 3 report: Team 17's final answers

Final text for each question, as agreed with Quincy and pasted into the team's Phase 3
draft. Kept here so the Phase 4 report can build on it. Evidence for each claim is in
[`docs/phase3.md`](../phase3.md). Citation numbers follow the report's reference list
([1] is the Cyber Resilience Act).

## Q1.1 Increment description

**Delivered capability:** Through the common HTTPS interface, a client can now submit a vulnerability report as a ticket, triage it as actively exploited (with an awareness time and a reason) or close it as not reportable, and read back the exact Article 14 deadlines with a live status for the early warning (24 hours), the vulnerability notification (72 hours), and the final report (14 days after a fix is available) [1, Art. 14(1)-(2)]. Tickets can also be updated, which recalculates the deadlines immediately, and every successful change is recorded in a per-ticket audit log. **Users/stakeholders:** the manufacturer's product security and compliance staff, who no longer track deadlines informally and risk missing them for reports that arrive outside working hours; reporters, whose contact details appear only in the single-ticket view; and Team 21 and the course staff, who test the service through its reset and fixed-clock controls. **Regulatory provision(s):** the reporting obligations for actively exploited vulnerabilities [1, Art. 14(1)-(2)(a)-(c)], the contact point for receiving vulnerability reports [1, Art. 13(17); Annex I, Part II(6)], and the definition of an actively exploited vulnerability [1, Art. 3(42)]. The increment is deployed on Google Cloud Run with a managed Postgres database, and our acceptance suite passed 55 of 55 tests against the evaluation deployment on October 17, 2026; Team 21's run against it is still pending.

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

We delivered the Phase 3 capability planned in Phase 2, Section 6.1: a deployed HTTPS service with authentication, test controls, ticket submission, triage, and deadline calculation (REQ-01 to REQ-04, REQ-12 to REQ-14, REQ-16), together with the planned automated validation (AC-01 to AC-05, AC-14, AC-15, and AC-17, with every response checked against the shared OpenAPI schemas), our base URL in the shared pod repository, and a team CI pipeline. Three planned items are not yet finished: the shared OpenAPI file is still a draft rather than frozen for the Phase 3 operations, the shared test file covering all eight Model D examples has been submitted to the pod's shared repository but not yet cross-checked by Team 21, and the pod has not yet run the shared suite against both deployments, since so far only our own suites have passed against our service. We also delivered part of the Phase 4 scope early: ticket updates with immediate deadline recalculation (REQ-06), per-ticket audit log entries, an ordered ticket list, and reporter confidentiality for the operations built so far. There were no instructor-required scope changes, and the pod has not changed or reduced the shared scope.

**To revisit before submitting:** update sentence 2 if the contract is frozen (Ann, 3.9), Team 21 approves the shared test file (pod-k-shared #8), or the cross-team runs happen (3.8).

## Q2.1 Deployed web service

Our service runs on Google Cloud Run in the us-central1 region as a Docker container (Python 3.12, Django with Django Ninja, served by gunicorn), backed by a managed Neon PostgreSQL database, with secrets such as database credentials and per-client API tokens stored in Google Secret Manager. Every release is built as a container image labeled with the exact Git commit it came from, so any running version maps back to a specific commit; changes merged to our main branch are tested in CI and deployed automatically to a separate development instance used only by our team, while the evaluation deployment is updated only through a manual release step that reruns the tests, applies database migrations, deploys, and checks the health endpoint. The service is reachable at all times but scales to zero when idle, so the first request after a quiet period takes about 3 to 6 seconds while an instance starts (plus about 1.5 seconds for the first database read), and it would become unavailable only if its $10 spending cap were reached, which stops it until we lift the cap manually. There is no rate limit, but it runs as a single instance that handles two requests at a time with a 30-second timeout and a 64 KB request size limit, all clients share one database and one test clock so test runs should be coordinated, and each team and the course staff have their own access token, which must be kept private.

**Choices made with Quincy:** no deployed version or hash named (the course staff can't see the repo, and it will change); "labeled with the exact Git commit" rather than "Git tags" (we don't create Git tags); `/test/reset` deliberately not mentioned (whether to keep or change it is a later discussion; it's required by REQ-16, so changing it needs Team 21).

## Q2.2 Registry and team documentation

Registry entry: Cross-team testing endpoint registry (Endpoint_Registry Google Sheet), Pod K, Team 17 row │ Updated on: October 17, 2026
Team documentation: https://github.com/team17-ece30861/pod-k-shared/blob/main/team17/SYSTEM.md │ Updated on: October 17, 2026

**Notes:** dates in this report use US Eastern time, the team's local date. Logs, test runs, and `docs/phase3.md` record UTC, which was already October 18 for the evening runs. The registry row holds the system URL, the tester (`pod-k-shared/team17/tester`), the spec (`pod-k-shared/spec.md`), and access notes, including that course staff get their token from Quincy.

## Q2.3 Operational experience supported by observability evidence

Our Phase 2 plan held up in practice: the service runs on Google Cloud Run with a persistent Neon PostgreSQL database and separate development and evaluation deployments, and tickets and their audit entries survive restarts and redeploys, changing only through the API or the pod's test reset control, which clears all tickets and audit entries so cross-team tests start from a known state. Secrets live in Google Secret Manager and are injected as environment variables at deploy time, with one API token per client (our team, Team 21, and the course staff) so each can be replaced independently, while GitHub Actions deploys through Workload Identity Federation without stored keys and database migrations run as a separate job before each release. To detect failures, the access log records every request with the name of the client whose token matched (never the token itself), the application logs each rejected request and a stack trace without request data for any server error, and Cloud Run's request log records each request's status code and latency; request bodies are never logged. In practice, failures have been caught by CI on every change, the health check after each deployment, our acceptance runs, and reviewing these logs, but unlike our plan we have not yet set up automated alerts beyond a budget alert, and we plan to add an alert on server errors in Phase 4. Over the last day, the evaluation deployment logged 0 server errors and 46 client errors, 43 from our acceptance suite's deliberately invalid requests and 3 from a browser opening the service without a token.

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

Integration: The new ticket operations are a router added to our existing Django Ninja API, backed by two new database tables (tickets and their audit entries) and pure domain functions for triage, deadlines, and statuses, while the platform layer built earlier is unchanged. A request passes through the platform middleware first (token check, body-size limit, and a database transaction), then the ticket route looks up and locks the ticket (404), checks the X-Actor header and the request body (400), and calls the domain rules with the service clock (409 for state conflicts, 422 for rule violations). On success the route saves the ticket and exactly one audit entry in the same transaction and builds the response from stored fields plus deadlines and statuses derived at read time; any error returns problem+json and rolls the transaction back, so a failed request changes nothing.

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

CI run: https://github.com/team17-ece30861/cra-service/actions/runs/39096210486 (our service repository is private; the run passed all 518 tests, lint, formatting, migration, and Django checks, then deployed to our development environment)

**To revisit:** if `cra-service` is made public, drop the "(our service repository is private…)" note. The repository history was scanned on 2026-10-18 before any visibility change: no secrets in any commit, branch, or CI log. Repository settings (Quincy, 2026-10-18): Actions limited to our organization, GitHub's own actions, and google-github-actions/auth and setup-gcloud; fork pull request workflows need approval; `main` requires a pull request.
