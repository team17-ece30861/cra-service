# Phase 4 report: Team 17's final answers

Final text for each question, as agreed with Quincy and entered in the team's Phase 4
document. Kept here so the Phase 5 report can build on it. Evidence for each claim is in
[`docs/system.md`](../system.md). Citation numbers follow the report's reference list
([1] is the Cyber Resilience Act).

## Q1.1 Increment description

**Delivered capability:** Through the common HTTPS interface, a client can now take an actively exploited vulnerability through the whole Article 14 reporting workflow: read the draft of each report (early warning, vulnerability notification, final report, and the user advisory) with any missing required fields listed, record when each report was actually submitted (which locks its content and marks it submitted or submitted late against its deadline), and close the ticket as resolved once all three reports are recorded [1, Art. 14(1)-(2)(a)-(c), 14(8)]. Ticket responses now show each report's live status and the next unmet deadline, the ticket list can be filtered by state and report status and is sorted by urgency, every change is in the audit log, and the reporter's details never appear anywhere but the single-ticket view. We also built a console where people on a manufacturer's security team sign in with their own account and do all of this in a browser, with their username recorded in the audit log. **Users/stakeholders:** the manufacturer's product security and compliance staff, who can see what's due next and send reports that are complete and on time; reporters, whose contact details stay private; and Team 21 and the course staff, who test the service through the common interface. **Regulatory provision(s):** the early warning, notification and final report obligations [1, Art. 14(1)-(2)(a)-(c)], informing users of the vulnerability and the measures they can take [1, Art. 14(8)], and the contact point for receiving vulnerability reports [1, Art. 13(17)]. The increment is deployed on Google Cloud Run [2] with a managed Neon PostgreSQL database [3], and our tester passed all 222 of its tests against the evaluation deployment on November 1, 2026.

REQ-05 - Obligation status │ Status: complete │ Demonstrated by: AC-06

REQ-06 - Updates and recalculation │ Status: complete │ Demonstrated by: AC-07 (an update that changes nothing now adds no audit entry, as agreed with Team 21)

REQ-07 - Report drafts │ Status: complete │ Demonstrated by: AC-08

REQ-08 - Recording submissions │ Status: complete │ Demonstrated by: AC-09

REQ-09 - Closure │ Status: complete │ Demonstrated by: AC-05, AC-10

REQ-10 - Listing │ Status: complete │ Demonstrated by: AC-11

REQ-11 - Audit log │ Status: complete │ Demonstrated by: AC-12

REQ-12 - Error handling │ Status: partial │ Demonstrated by: AC-02, AC-04, AC-14, and every error response in our tester checked against the contract │ Missing: our own run of the 500 generated malformed requests (AC-13), moved to Phase 5. Team 21's tester did send 500 malformed requests to our evaluation deployment on November 1, with no server errors and no data stored

REQ-15 - Reporter confidentiality │ Status: complete │ Demonstrated by: AC-16

## Q1.2 Comparison with the Phase 2 plan

We delivered the Phase 4 capability planned in Phase 2, Section 6.2: the full reporting workflow of report status, all four drafts, submission recording, closure, filtered listing, the audit log, and reporter confidentiality (REQ-05 to REQ-11, REQ-15), with automated tests for AC-06 to AC-12 and AC-16, our cross-team tester published for Team 21, and the first full cross-team run in both directions on November 1. Not delivered: the 500 generated malformed requests (AC-13) moved to Phase 5, the shared test file still has only the Model D examples (no Phase 4 cases yet), the updated contract is in a pull request waiting on Team 21's approval, and one spec disagreement from the cross-team run (whether a 422 must list every problem) is raised but not yet resolved. The scripted incident (submit, triage, three submissions, close) now passes against Team 21's service, along with the rest of our 222 tests, after they fixed the mismatches our first run found that morning. There were no instructor-required scope changes; we also built a sign-in console early, which Phase 2 planned as each team's own intake channel in Phase 5, without changing the shared scope.

## Q2.1 Deployed web service

Our service runs on Google Cloud Run [2] in the us-central1 region as a Docker container (Python 3.12, Django [4] with Django Ninja [5], served by gunicorn), backed by a managed Neon PostgreSQL database [3], with database credentials and per-client API tokens stored in Google Secret Manager [6]; the same service also hosts our console at /console/, where people sign in with their own accounts instead of a token. Every release is a container image labeled with the exact Git commit it came from; changes merged to our main branch are tested in CI and deployed automatically to a development instance only our team uses, while the evaluation deployment changes only through a manual release step that reruns the tests, applies database migrations, deploys, and checks the health endpoint. The service is reachable at all times but scales to zero when idle, so the first request after a quiet period takes about 3 to 6 seconds (plus about 1.5 seconds for the first database read), and it would stop only if its $10 spending cap were reached, until we lift it by hand. There's no rate limit, but it runs as a single instance handling two requests at a time with a 30-minute timeout (long enough for a full run of our tester) and a 64 KB request limit; all clients share one database and one test clock, so test runs should be one at a time, and each team and the course staff have their own access token, which must be kept private.

## Q2.2 Registry and team documentation

Registry entry: Cross-team testing endpoint registry (Endpoint_Registry Google Sheet), Pod K, Team 17 row (system URL, our tester, the pod spec, and access notes) │ Updated on: November 1, 2026

Team documentation: https://github.com/team17-ece30861/pod-k-shared/blob/main/team17/SYSTEM.md (the system as delivered in Phase 4: operations, the console, models, interfaces, test results, and known limitations; the source is docs/system.md in our repository) │ Updated on: November 1, 2026

## Q2.3 Operational experience supported by observability evidence

Our Phase 2 plan has held up: tickets, recorded reports, and audit entries live in a persistent Neon PostgreSQL database that survives restarts and redeploys and changes only through the API, the console, or the pod's test reset (which clears tickets, reports, and audit entries but keeps the fixed test clock and test sessions). Secrets live in Google Secret Manager and are injected at deploy time, with one API token per client so each can be replaced on its own, and GitHub Actions deploys through Workload Identity Federation [7] without stored keys. To detect failures, the access log records every request with the name of the client whose token matched (never the token), the application logs each rejected request and a stack trace without request data for any server error, and Cloud Run's request log records each request's status and latency; request bodies are never logged. We still rely on CI, the post-deploy health check, our test runs, and reading these logs rather than an automated alert (only a $1 budget alert is set up): the server-error alert we planned for Phase 4 moved to Phase 5. Since the Phase 4 release, the evaluation deployment has logged 0 server errors and 512 client errors, 503 of them from Team 21's suite deliberately sending invalid requests on November 1.

Excerpt from the evaluation deployment's logs during Team 21's test run (November 1, 2026, 3:12 PM Eastern; times shown in UTC):

```
# Access log: the client is identified by name, never by token
169.254.169.126 - team21 [01/Nov/2026:20:12:54 +0000] "POST /tickets/<id>/reports/early_warning/submission HTTP/1.1" 200 443 "-" "python-httpx/0.28.1"
169.254.169.126 - team21 [01/Nov/2026:20:13:00 +0000] "POST /tickets/<id>/reports/notification/submission HTTP/1.1" 409 94 "-" "python-httpx/0.28.1"
# Cloud Run request log: method, status, latency
2026-11-01T20:13:04Z  POST  200  0.387 s  /tickets/<id>/close
```

## Q3.1 Operation status

Generated by our tester from its run against the evaluation deployment on November 1, 2026 (222 of 222 tests passed). "Checked" lists the status codes the tester observed for each operation, every response body was validated against the contract, and nothing is reported as passing that wasn't observed.

GET /health │ Requirement(s): none (public health check) │ Implemented: yes │ Success responses conform: yes │ Error responses conform: none defined in the contract

POST /tickets │ Requirement(s): REQ-01, REQ-12, REQ-13, REQ-14 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (400, 401, 413 checked)

GET /tickets │ Requirement(s): REQ-10, REQ-15 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (400, 401 checked)

GET /tickets/{id} │ Requirement(s): REQ-04, REQ-05, REQ-15 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (401, 404 checked)

PATCH /tickets/{id} │ Requirement(s): REQ-04, REQ-06 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (400, 401, 409, 422 checked; 404 and 413 not yet checked by the HTTP tester, see LIM-11)

POST /tickets/{id}/triage │ Requirement(s): REQ-02, REQ-03, REQ-04 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (400, 401, 409, 422 checked; 404 and 413 not yet checked by the HTTP tester)

GET /tickets/{id}/reports/{type} │ Requirement(s): REQ-07, REQ-15 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (401, 404, 409 checked)

POST /tickets/{id}/reports/{type}/submission │ Requirement(s): REQ-05, REQ-08 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (400, 401, 404, 409, 413, 422 checked)

POST /tickets/{id}/close │ Requirement(s): REQ-09 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (400, 401, 404, 409 checked)

GET /tickets/{id}/audit │ Requirement(s): REQ-11 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (401, 404 checked; 405 for editing or deleting the log is checked by a separate tester case outside this table)

POST /test/reset │ Requirement(s): REQ-16 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (401 checked)

GET /test/clock │ Requirement(s): REQ-16 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (401 checked)

PUT /test/clock │ Requirement(s): REQ-16 │ Implemented: yes │ Success responses conform: yes │ Error responses conform: yes (400, 401 checked)

DELETE /test/clock │ Requirement(s): REQ-16 │ Implemented: yes │ Success responses conform: yes (204, returned by the run's cleanup step, but no tester case checks it yet) │ Error responses conform: yes (401 checked)

Integration: Phase 4 added routes to our existing ticket router (drafts, record submission, close, and list filters), one new table for recorded reports, pure domain rules (building drafts from Model C, checking a submission or a close, and ordering the list), and a console whose pages call the same route functions directly with the signed-in username as the X-Actor, so every rule and audit entry is shared with the API; the platform layer from Phase 3 is unchanged. A request still passes through the platform middleware first (token check, body-size limit, and one database transaction), then the route looks up and locks the ticket (404), checks the X-Actor header and the body (400), and calls the domain rule with the service clock (409 for state conflicts before 422 for rule violations). Recording a report stores a locked copy of the draft and exactly one audit entry in the same transaction, and every ticket response now computes each report's status from its recorded submission and current deadline, so drafts, tickets, and the list always agree; errors return problem+json [8] and roll the transaction back.

## Q3.2 Contract changes and pod communication

**Contract version at delivery:** 0.1.0-draft (published in our pod's shared repo on October 18, 2026).

**Changes since Phase 2:** None to the operations, schemas or status codes; Team 21 agreed to our answers for seven of the ten gaps we raised this phase (for example, an update that changes nothing adds no audit entry), which are written into a freeze PR that bumps the contract to 0.2.0 (pod-k-shared PR #14, waiting on Team 21's approval), and two answers that change the contract itself will come as their own PRs in Phase 5.

**Pod agreement:** Team 21 agreed by email on November 1, 2026 (replying to our October 27 email), and every contract change goes through a pull request in the shared repo that the other team approves.

**Intentional deviations and resolution plan:** The 0.1.0-draft text says every successful update adds exactly one audit entry, but ours adds none when the update changes nothing (Q6, agreed by both teams); the deviation ends when PR #14 merges and is listed in our public testing guide until then.


## Q4.1 Test runner and execution instructions

**Base URL override:** Point the suite at https://team17-prod-7zneiwx4ba-uc.a.run.app (the base URL, with no path prefix) and send "Authorization: Bearer <token>" on every request except GET /health. Our own tester takes any team's base URL the same way, through the CRA_BASE_URL environment variable or the --base-url option, with no code changes. │ **Response received:** GET /health returned 200 with body {"status": "ok"} (November 1, 2026), and a protected route without a token returned 401 with {"title": "Unauthorized", "status": 401} as application/problem+json. │ **Conforms to spec:** yes. Our tester checks every response against the OpenAPI spec, and all 222 tests passed against this deployment on November 1, 2026.

**Known deviations from the OpenAPI spec:** The contract text says every successful update adds an audit entry, but an update that changes nothing adds none (pod question Q6). It goes away when the contract freeze PR merges (see Q3.2).


## Q4.2 Tests for new functionality

All tests below are in our tester (`acceptance/`), which runs over HTTP against any deployment and, in CI, against the service locally; file names are shortened: drafts = `draft_cases.py`, submissions = `submission_cases.py`, closure = `closure_cases.py`, listing = `listing_cases.py`, updates = `update_cases.py`, privacy = `privacy_cases.py`, phase 3 = `cases.py`.

AC-06 │ Requirement(s): REQ-05 │ Test(s): listing `test_ac06_steps_through_e6_and_records_on_time_and_late` (success and boundary), `test_ac06_a_report_recorded_exactly_at_its_due_time_is_on_time` (boundary), `test_ac06_moving_the_clock_back_does_not_change_a_recorded_status` (success), `test_q4_an_earlier_awareness_can_make_a_recorded_report_late` (success) │ Type: success, boundary │ Automated: yes (unsubmitted statuses were covered in Phase 3)

AC-08 │ Requirement(s): REQ-07, REQ-15 │ Test(s): drafts `test_ac08_complete_live_draft_matches_model_c` (success, all four types), `test_ac08_missing_fields_follow_each_ticket_update` (success), `test_ac08_never_reportable_ticket_returns_409` (failure), `test_ac08_unknown_report_type_precedes_nonreportable_state` (failure) │ Type: success, failure │ Automated: yes

AC-09 │ Requirement(s): REQ-08 │ Test(s): submissions `test_ac09_records_locked_content_and_one_audit_entry` (success), `test_ac09_locked_content_survives_product_edits` (success), `test_ac09_predecessor_conflict_precedes_missing_fields_and_future_time` (failure: 409), `test_ac09_duplicate_precedes_missing_fields_and_future_time` (failure: 409), `test_ac09_reports_missing_fields_and_time_together` (failure: 422), `test_ac09_submission_interval_is_inclusive` (boundary) │ Type: success, failure, boundary │ Automated: yes

AC-10 │ Requirement(s): REQ-09 │ Test(s): closure `test_ac10_all_three_reports_allow_one_atomic_close_and_remain_readable` (success), `test_ac10_outstanding_reports_reject_closure_without_changes` (failure: 409), `test_ac10_never_reportable_tickets_cannot_be_resolved` (failure: 409), `test_ac10_resolved_ticket_rejects_every_change` (failure: 409) │ Type: success, failure │ Automated: yes

AC-11 │ Requirement(s): REQ-10 │ Test(s): listing `test_ac11_unfiltered_list_is_nearest_unmet_deadline_first` (success), `test_ac11_filters_return_exactly_the_expected_tickets_in_order` (success), `test_ac11_status_filters_follow_recorded_reports` (success), `test_ac11_unknown_filter_values_are_rejected` (failure: 400), `test_q2_ties_go_to_the_ticket_received_first` (success) │ Type: success, failure │ Automated: yes

AC-12 │ Requirement(s): REQ-11 │ Test(s): closure `test_ac12_scripted_lifecycle_has_exact_immutable_audit_sequence` (success, with failed requests mixed in); submissions `test_ac09_full_recording_sequence_has_no_audit_gaps_after_failures` (failure); phase 3 `test_audit_cannot_be_edited_or_deleted` (failure: 405), `test_audit_unknown_ticket_is_404_and_changes_nothing` (failure: 404); updates `test_q6_a_patch_that_changes_nothing_adds_no_audit_entry` (success) │ Type: success, failure │ Automated: yes

AC-13 │ Requirement(s): REQ-12 │ Test(s): none in our suite yet; Team 21's tester ran its AC-13 check (500 malformed requests) against our evaluation deployment on November 1 and passed, with no server errors and no data stored (failure) │ Type: failure │ Automated: not in our suite yet (our generated run with Schemathesis moved to Phase 5); yes in Team 21's tester. Every error response in our 222 tests is also checked against the contract's error format.

AC-16 │ Requirement(s): REQ-15 │ Test(s): privacy `test_ac16_reporter_appears_only_in_the_single_ticket_response` (success and failure: every read, plus errors on the same ticket); `tests/test_privacy_api.py` (failure: no log line contains the reporter); reporter checks inside the drafts, submissions and closure tests │ Type: success, failure │ Automated: yes

**Oracles:** Expected values come from the pod spec, worked out by hand, never copied from our service's output. Deadlines and statuses come from Model D (all eight examples are in the pod's shared test file, which Team 21 checked), required fields per draft come straight from the Model C table, and status codes and their order come from the OpenAPI contract, which our tester also uses to check every response body. We trust them because they were written independently of the code, the tests for behavior we changed were checked to fail against the old code, and Team 21's independently built service passed 202 of the same 222 tests on its first run (every failure traced to a specific line in the contract or Model C, or to one spec gap, see Q6.2) and all 222 after their fixes.

## Q4.3 Regression and static checks

Every push and pull request runs our full CI pipeline in GitHub Actions, and nothing is deployed unless it passes (none of the 100 runs on our main branch so far has failed: 94 passed and 6 were cancelled when a newer commit replaced them). The pipeline runs the complete test suite against a real PostgreSQL 18 database, which re-runs every earlier platform, unit and integration test along with the Phase 3 and Phase 4 tester cases (1,231 tests in the run linked below, up from 518 in Phase 3). The tester checks every response against the shared OpenAPI contract, so new phases are held to the same contract tests as the old ones, and the full tester was re-run over HTTPS against our development deployment before this phase's release (222 of 222 passed). When we changed behavior this phase, we wrote the test first and checked that it failed against the old code, and every code change had an independent review posted on its pull request before it merged.

CI run: https://github.com/team17-ece30861/cra-service/actions/runs/41331009700

## Q4.4 Static checks

Our static checks haven't changed since Phase 3: CI runs ruff (linting and formatting), a check for missing database migrations, Django's system checks, and contract validation of every tester response on every push and pull request, and Dependabot alerts and secret scanning with push protection are still on (we still don't use a type checker or pre-commit hooks). A failing check blocks both merging and deployment, because main only accepts pull requests whose CI passes and both deployments run only after the full suite passes.

CI run: https://github.com/team17-ece30861/cra-service/actions/runs/41331009700

## Q4.5 Test results against the deployed system

Run date/time: November 1, 2026, 5:02 to 5:13 PM Eastern (22:02 to 22:13 UTC) │ Version tested: de7a056 │ Tests run: 222 │ Passed: 222 │ Failed: 0 │ Skipped: 0

Failures: none. Our deployed tester ran the full suite over HTTPS against our evaluation deployment at the released version and passed every test, with every response validated against the shared contract; afterward we reset the deployment and released its clock. An earlier run from outside Google, against the previous release with the same API code, also passed 222 of 222.

## Q5.1 Model updates

Model A: Ticket lifecycle (state machine) │ Changed: yes │ What changed and why: Recording the three reports and closing a reportable ticket as resolved are now delivered, so the Phase 3 dotted parts are solid. The reportable state now lists what can be read and recorded (all four drafts, and the three reports once each, in order), and each closed state says whether drafts are still readable. │ Location: https://github.com/team17-ece30861/cra-service/blob/main/docs/models/model-a-ticket-lifecycle.png

Model B: Report status (state machine) │ Changed: yes │ What changed and why: submitted and submitted_late are now delivered. We added overdue → submitted (a report recorded with a submitted_at at or before its due time) and two-way submitted ↔ submitted_late transitions for when a later edit moves the deadline, which the pod agreed on this phase (Q4); Phase 2 drew the submitted statuses as final. We also added the transitions for three cases that were always possible but never drawn: a report can already be overdue at triage (as in Model D's E1), a fix time given at intake skips awaiting_fix, and clearing the fix time sends an unrecorded final report back to awaiting_fix. │ Location: https://github.com/team17-ece30861/cra-service/blob/main/docs/models/model-b-report-status.png

Model C: Required fields per draft (table) │ Changed: no │ What changed and why: Drafts are delivered exactly as the table says, and our tester checks every draft against it. The early warning's required fields are still stricter than Article 14(2)(a) [1]; the pod agreed to allow "unknown" values, which needs a contract change in Phase 5. │ Location: Phase 2, Section 3.2 (unchanged); also https://github.com/team17-ece30861/pod-k-shared/blob/main/spec.md

Model D: Deadline examples (table) │ Changed: no │ What changed and why: The delivered service still reproduces all eight examples exactly, as checked by the pod's shared test file, which Team 21 has now checked too. │ Location: Phase 2, Section 3.2 (unchanged); also https://github.com/team17-ece30861/pod-k-shared/blob/main/spec.md

Architecture and data flow (component diagram, Section 7.1) │ Changed: yes │ What changed and why: We added what Phase 4 delivered: the draft, submission and close routes, the draft builder and the submission, close and listing rules, the table that stores recorded reports, and our console, which people sign in to with their own account instead of the API token. We also added the course's cross-team testing interface (test setup and report, our deployed tester and the subprocess that runs it, and their session tables), which existed in Phase 3 but was missing from that drawing. │ Location: https://github.com/team17-ece30861/cra-service/blob/main/docs/models/architecture.png

Updated diagrams: all models, with their sources and change notes, are at https://github.com/team17-ece30861/cra-service/tree/main/docs/models. Everything drawn now exists in the delivered system.

## Q5.2 Model-implementation consistency

We checked each updated model against the code rather than generating it from the code: every state transition was traced to the domain function that implements it and the test that exercises it, every component and table in the architecture diagram was matched to a real module or model, and a separate AI session that hadn't drawn the diagrams repeated the check, finding three missing Model B transitions and the missing console, which we fixed before publishing. Model C and Model D are also checked automatically, since our tester asserts Model D's exact deadlines and statuses and Model C's required fields on every run against a deployment. One divergence was in Model B: the Phase 2 model ended at submitted and submitted_late, but the delivered system recalculates a recorded report's status against its current deadline, so an edit that moves the deadline can switch it between the two. The pod agreed this was the right behavior (Q4), so we corrected the model, not the code.

## Q6.1 Cross-team test

On November 1, 2026, both directions ran with the Phase 4 operations included: our first run against Team 21 that morning passed 202 of 222 tests, and we sent them the 20 failures by email (mostly error precedence, plus a 405 format, an X-Actor length check, the user advisory's fields, and one spec gap). Team 21 fixed them and moved to a new deployment, and our rerun against it that afternoon passed all 222. Team 21's suite passed all of its tests against our evaluation deployment the same afternoon.

Our tests → Team 21 service │ Date: November 1, 2026, 3:47 PM Eastern │ Run/passed: 222/222 (first run that morning, against their earlier deployment: 202/222) │ Main problem and owner: none in this run; the morning run's failures were Team 21's error precedence and three smaller contract mismatches (owner: Team 21, fixed the same day), plus whether a 422 must list every problem (owner: the pod, see Q6.2) │ Coverage: code: not available (Team 21's service doesn't report it to our tester); component: not measured (the pod spec doesn't define a component list); system: 15 of 19 acceptance criteria (AC-01 to AC-06, AC-08 to AC-12, AC-14 to AC-17), including all eight Model D examples.

Team 21 tests → our service │ Date: November 1, 2026, 3:12 PM Eastern │ Run/passed: 17/17 │ Main problem and owner: none │ Coverage: code: not reported (our course test interface doesn't instrument source lines); component: not measured; system: 17 of 19 acceptance criteria, one test each for AC-01 to AC-17 (including 500 malformed requests for AC-13, which produced no server errors), and our logs show it exercised every Phase 4 operation (drafts, recording submissions, closing, and list filters) along with intake, triage, updates, the audit log, reset, and the clock.

## Q6.2 Specification issues discovered

Issue: Recording a submission (POST /tickets/{id}/reports/{type}/submission, REQ-08, AC-09): when a request breaks more than one rule (for example, an early warning with no member states and a submitted_at in the future), the contract says the answer is 422 but not whether every problem has to be listed. │ Effect: Our service lists both problems and our tester expects both, so Team 21's first deployment, which listed only the first, failed that test even though neither service broke the contract (their new deployment lists both, but nothing in the contract requires it). │ Pod decision or plan: We raised it with Team 21 by email on November 1, 2026, and plan to settle it with a contract change in the shared repo early in Phase 5. Until then, we'll treat a 422 that names at least one of the problems as passing in cross-team runs.

## Q7.1 What changed and what remains incomplete

Changed since Phase 2:
- The service is deployed on Google Cloud Run with a Neon PostgreSQL database, per-client bearer tokens, the X-Actor check, a 64 KB request limit, and contract-format errors in the agreed precedence order (REQ-12, REQ-14; AC-02, AC-15).
- Ticket intake, triage, exact Article 14 deadlines, and updates with recalculation, delivered in Phase 3 (REQ-01 to REQ-04, REQ-06; AC-01, AC-03 to AC-05, AC-07, AC-14).
- New in Phase 4: report drafts for all four reports, recording submissions with locked content and submitted or submitted-late statuses, closing a reportable ticket as resolved, filtered and urgency-sorted listing, the complete audit log, and reporter confidentiality everywhere (REQ-05, REQ-07 to REQ-11, REQ-15; AC-06, AC-08 to AC-12, AC-16).
- A console where people sign in with their own accounts and work through the whole workflow in a browser, built in the same service on the same rules as the API.
- Testing infrastructure: a 222-test tester that checks every response against the contract and runs against any team's service, CI that blocks merging on any failure, an independent review on every code change, and the pod's shared repository with our tester, testing guide, and the shared Model D test file (now checked by Team 21).

Remaining incomplete:
- Our own run of the 500 generated malformed requests (REQ-12; AC-13), moved to Phase 5. Team 21's tester did send 500 malformed requests to our evaluation deployment on November 1, with no server errors.
- The performance target with 1,000 tickets and the recorded restart demonstration (REQ-17, REQ-18; AC-18, AC-19), planned for Phase 5.
- Pod items: Team 21's approval of the contract freeze, the two agreed contract changes (future fix times, "unknown" member states for REQ-08 and AC-09), the unanswered workaround question for the final report deadline (REQ-04), Phase 4 cases in the shared test file, and the spec decision on 422s that list several problems (AC-09).
- An automated alert on server errors, promised in Phase 3 for Phase 4 and moved to Phase 5.

## Q7.2 Known limitations and defects

LIM-01 │ All clients share one database and one test clock, so a test reset deletes everyone's data and two suites running at once interfere │ Affects: REQ-16; all operations │ Severity: medium │ Workaround for podmates: run one suite at a time, and finish by resetting and releasing the clock │ Target phase: none planned (required by the shared test design)

LIM-02 │ The service scales to zero: the first request after idle takes about 3 to 6 seconds, plus about 1.5 seconds for the first database read. It runs one instance with two workers and a 30-minute timeout, and the 1-second target with 1,000 tickets (REQ-17) hasn't been measured on the deployed service yet │ Affects: REQ-17; all operations │ Severity: medium │ Workaround for podmates: send GET /health and one authenticated read before timing anything, use timeouts of at least 30 seconds, and send requests one at a time │ Target phase: 5

LIM-03 │ A $10 spending cap stops the service until we lift it manually, and there's still no automated alert for server errors (we planned it for Phase 4 and moved it to Phase 5) │ Affects: availability of all operations │ Severity: medium │ Workaround for podmates: if the service stops responding, email Team 17 │ Target phase: 5

LIM-04 │ The final report deadline starts only from the recorded fix time, while the CRA starts it when any corrective or mitigating measure is available [1, Art. 14(2)(c)], so a workaround released before the fix can leave our due time later than the regulation requires. The pod hasn't answered this yet │ Affects: REQ-04; final report deadline │ Severity: medium │ Workaround for podmates: record the time of the first mitigating measure as the fix time │ Target phase: 5 (pod decision)

LIM-05 │ Two agreed pod answers aren't in force yet because they change the contract: a ticket submitted with a future fix time is still accepted (201), and an early warning still requires member states and affected versions (no "unknown" option) │ Affects: REQ-01, REQ-08; POST /tickets, POST /tickets/{id}/reports/early_warning/submission │ Severity: low │ Workaround for podmates: don't assert either new behavior until the contract PRs merge │ Target phase: 5

LIM-06 │ Until the contract freeze PR merges, the contract text says every successful update adds an audit entry, but ours adds none when the update changes nothing (agreed with Team 21) │ Affects: REQ-11; PATCH /tickets/{id} │ Severity: low │ Workaround for podmates: follow the agreed answer (Q6) in our testing guide │ Target phase: 4 or 5 (when Team 21 approves the PR)

LIM-07 │ An update that changes a real field and also sends an empty list for a list that was never set records that list as a change in the audit entry, even though no read shows a difference │ Affects: REQ-11; PATCH /tickets/{id} │ Severity: low │ Workaround for podmates: don't count audit changes on mixed updates that include empty lists │ Target phase: 5

LIM-08 │ No rate limiting, and bearer tokens are long-lived and rotated only by hand │ Affects: REQ-14; all operations │ Severity: low │ Workaround for podmates: keep your token private and tell us if it may have leaked, so we can replace it │ Target phase: 5

LIM-09 │ GET /health returns 200 even if the database is unreachable, and HEAD /health requires a token │ Affects: GET /health │ Severity: low │ Workaround for podmates: use an authenticated GET /tickets to check that the service is fully working, and GET (not HEAD) for health checks │ Target phase: 5

LIM-10 │ Google Cloud Run's front end rejects any GET request that has a body before it reaches our service, returning a dropped connection or an HTML 400 instead of our problem+json error │ Affects: REQ-12; all GET operations │ Severity: low │ Workaround for podmates: don't send request bodies with GET │ Target phase: none planned (hosting platform behavior)

LIM-11 │ Test gaps: the 500 generated malformed requests (AC-13) haven't been run, the update cases (AC-07) are tested in CI but not yet in our HTTP tester, and a few error codes have no test (404 and 413 on PATCH and triage, 405 on the audit log in the generated table). No tests are currently failing │ Affects: REQ-06, REQ-11, REQ-12 │ Severity: low │ Workaround for podmates: none needed │ Target phase: 5

LIM-12 │ The console has no limit on failed sign-ins, so someone could keep guessing a person's password │ Affects: the console at /console/ (not the API, which uses bearer tokens) │ Severity: low │ Workaround for podmates: none needed, since podmates use the API; we use long, unique passwords for console accounts │ Target phase: 5

LIM-13 │ Our deployed tester (the course testing interface at /tester) doesn't clean up after a run: it leaves the target's test clock fixed and the run's test data in place │ Affects: REQ-16; any system our deployed tester runs against │ Severity: low │ Workaround for podmates: after a run of our deployed tester, call POST /test/reset and DELETE /test/clock (every test also resets first, so the next run isn't affected) │ Target phase: 5


## Q7.3 Adjustments to next phase milestone

The Phase 5 milestone in Phase 2, Section 6.3 still holds, and part of it is already done: each team's own intake channel, which we delivered early as the sign-in console. Phase 5 gains four items that slipped from Phase 4: the 500 generated malformed requests (AC-13), the automated alert on server errors, the early performance check we promised in the Phase 3 report and didn't get to, and the pod follow-ups from this phase (two contract changes Team 21 agreed to, the open workaround question, and the 422 disagreement). The contract changes need Team 21's approval by pull request, as before; the rest is within our team. We'll run the performance check first in Phase 5, since it's the biggest remaining unknown.

Priority risks from Phase 2, Section 9.1:
- Reduced: Risk 2 (cross-team compatibility). Our tester passed 202 of 222 tests against Team 21's first deployment, with every failure traced to the contract, Model C, or one spec gap, and all 222 after their fixes; Team 21's suite passed all 17 of its tests against ours the same day.
- Remains, smaller: Risk 1 (our reading of the CRA). The pod agreed to relax the early warning's required fields, but the question of whether a workaround starts the final report clock [1, Art. 14(2)(c)] is still unanswered, so our final report deadline may still be later than the regulation requires.
- Remains: Hosting performance. The service scales to zero and runs as one instance, and the 1-second target with 1,000 tickets (REQ-17) still hasn't been measured on the deployed service.
- New: Contract drift. Seven agreed answers and two agreed changes aren't in the published contract yet, so a podmate reading only the contract could file agreed behavior as a bug until the freeze PR and the two change PRs merge.

## Q8.1 Actual GenAI use

Each teammate answers for themselves in the submitted document.

## Q9 References

[1] European Parliament and Council of the European Union. "Regulation (EU) 2024/2847 (Cyber Resilience Act)." October 23, 2024. https://eur-lex.europa.eu/eli/reg/2024/2847/oj. Accessed: 2026-11-01.

[2] Google Cloud. "Cloud Run documentation." https://docs.cloud.google.com/run/docs. Accessed: 2026-11-01.

[3] Neon. "Neon documentation." https://neon.com/docs/introduction. Accessed: 2026-11-01.

[4] Django Software Foundation. "Django documentation." Version 5.2. https://docs.djangoproject.com/en/5.2/. Accessed: 2026-11-01.

[5] Django Ninja. "Django Ninja." Version 1.x. https://django-ninja.dev/. Accessed: 2026-11-01.

[6] Google Cloud. "Secret Manager documentation." https://docs.cloud.google.com/secret-manager/docs. Accessed: 2026-11-01.

[7] Google Cloud. "Workload Identity Federation." Identity and Access Management (IAM) documentation. https://docs.cloud.google.com/iam/docs/workload-identity-federation. Accessed: 2026-11-01.

[8] Internet Engineering Task Force (IETF). "RFC 9457: Problem Details for HTTP APIs." July 2023. https://www.rfc-editor.org/rfc/rfc9457.html. Accessed: 2026-11-01.
