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
