# Phase 3 report: Team 17's final answers

Final text for each question, as agreed with Quincy and pasted into the team's Phase 3
draft. Kept here so the Phase 4 report can build on it. Evidence for each claim is in
[`docs/phase3.md`](../phase3.md). Citation numbers follow the report's reference list
([1] is the Cyber Resilience Act).

## Q1.1 Increment description

**Delivered capability:** Through the common HTTPS interface, a client can now submit a vulnerability report as a ticket, triage it as actively exploited (with an awareness time and a reason) or close it as not reportable, and read back the exact Article 14 deadlines with a live status for the early warning (24 hours), the vulnerability notification (72 hours), and the final report (14 days after a fix is available) [1, Art. 14(1)-(2)]. Tickets can also be updated, which recalculates the deadlines immediately, and every successful change is recorded in a per-ticket audit log. **Users/stakeholders:** the manufacturer's product security and compliance staff, who no longer track deadlines informally and risk missing them for reports that arrive outside working hours; reporters, whose contact details appear only in the single-ticket view; and Team 21 and the course staff, who test the service through its reset and fixed-clock controls. **Regulatory provision(s):** the reporting obligations for actively exploited vulnerabilities [1, Art. 14(1)-(2)(a)-(c)], the contact point for receiving vulnerability reports [1, Art. 13(17); Annex I, Part II(6)], and the definition of an actively exploited vulnerability [1, Art. 3(42)]. The increment is deployed on Google Cloud Run with a managed Postgres database, and our acceptance suite passed 55 of 55 tests against the evaluation deployment on October 18, 2026; Team 21's run against it is still pending.

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
REQ-18 - Persistence │ Status: complete │ Demonstrated by: a ticket and its audit log read back unchanged after a new deployment replaced the running service (October 18, 2026); the recorded demonstration in AC-19 is planned for Phase 5

**To revisit before submitting:** if Team 21 runs their suite against us first, update the last sentence of the narrative.

## Q1.2 Comparison with the Phase 2 plan

We delivered the Phase 3 capability planned in Phase 2, Section 6.1: a deployed HTTPS service with authentication, test controls, ticket submission, triage, and deadline calculation (REQ-01 to REQ-04, REQ-12 to REQ-14, REQ-16), together with the planned automated validation (AC-01 to AC-05, AC-14, AC-15, and AC-17, with every response checked against the shared OpenAPI schemas), our base URL in the shared pod repository, and a team CI pipeline. Three planned items are not yet finished: the shared OpenAPI file is still a draft rather than frozen for the Phase 3 operations, the shared test file covering all eight Model D examples has been submitted to the pod's shared repository but not yet cross-checked by Team 21, and the pod has not yet run the shared suite against both deployments, since so far only our own suites have passed against our service. We also delivered part of the Phase 4 scope early: ticket updates with immediate deadline recalculation (REQ-06), per-ticket audit log entries, an ordered ticket list, and reporter confidentiality for the operations built so far. There were no instructor-required scope changes, and the pod has not changed or reduced the shared scope.

**To revisit before submitting:** update sentence 2 if the contract is frozen (Ann, 3.9), Team 21 approves the shared test file (pod-k-shared #8), or the cross-team runs happen (3.8).

## Q2.1 Deployed web service

Our service runs on Google Cloud Run in the us-central1 region as a Docker container (Python 3.12, Django with Django Ninja, served by gunicorn), backed by a managed Neon PostgreSQL database, with secrets such as database credentials and per-client API tokens stored in Google Secret Manager. Every release is built as a container image labeled with the exact Git commit it came from, so any running version maps back to a specific commit; changes merged to our main branch are tested in CI and deployed automatically to a separate development instance used only by our team, while the evaluation deployment is updated only through a manual release step that reruns the tests, applies database migrations, deploys, and checks the health endpoint. The service is reachable at all times but scales to zero when idle, so the first request after a quiet period takes about 3 to 6 seconds while an instance starts (plus about 1.5 seconds for the first database read), and it would become unavailable only if its $10 spending cap were reached, which stops it until we lift the cap manually. There is no rate limit, but it runs as a single instance that handles two requests at a time with a 30-second timeout and a 64 KB request size limit, all clients share one database and one test clock so test runs should be coordinated, and each team and the course staff have their own access token, which must be kept private.

**Choices made with Quincy:** no deployed version or hash named (the course staff can't see the repo, and it will change); "labeled with the exact Git commit" rather than "Git tags" (we don't create Git tags); `/test/reset` deliberately not mentioned (whether to keep or change it is a later discussion; it's required by REQ-16, so changing it needs Team 21).
