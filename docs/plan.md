# Project plan (Phases 3 to 5)

The working plan for Team 17's CRA reporting service: who owns what, what's done, and
what's next. It's written for teammates and their coding agents (Claude Code and Codex).
Last updated 2026-10-26.

**Agents: read this first.** Then read [`CLAUDE.md`](../CLAUDE.md) (repository rules; they
apply to every agent, not just Claude), [spec.md](spec.md) (the agreed behavior),
and [`openapi.yaml`](../openapi.yaml) (the contract). Pick a task from your owner's
section below, and update its status row in the same PR that finishes it.

## Sources of truth

| Question | Where to look |
|---|---|
| What must the API accept and return? | [`openapi.yaml`](../openapi.yaml). Ninja's `/docs` is not the contract. |
| What are the rules, models, deadlines, and acceptance criteria? | [spec.md](spec.md), copied from the Phase 2 report |
| Repository rules (clock, UTC, errors, X-Actor, logging, branches) | [`CLAUDE.md`](../CLAUDE.md) |
| Hosting, deploys, rollback, cost, platform interpretations | [platform.md](platform.md), [`README.md`](../README.md) |
| Why something was decided, and what's already settled | [decisions.md](decisions.md) |
| The system as delivered (models, interfaces, limitations), domain helpers, triage rules | `docs/phase3.md`, `docs/domain.md`, `docs/triage.md` |
| What each teammate is in the middle of and waiting on | `docs/handoff/` (one file per person) |

## Team and ownership

| Area | Owner | Owns |
|---|---|---|
| Platform and Hosting | Quincy (Claude Code) | Cloud Run, deploy pipeline, CI, secrets, budget caps. Config, database, migrations. Auth, X-Actor, problem+json errors, logging. `/test/reset`, `/test/clock`. Deployed URLs, the shared pod file entry, the class registry entry. Merge and release coordination. |
| API and Data | Ann (Codex) | Ticket, triage, report, and audit endpoints: validation, status codes, and responses that match `openapi.yaml`. Models and migrations for tickets, submissions, and audit entries. Schemathesis contract tests. Keeping `openapi.yaml` in sync with Team 21. |
| Domain Logic and Testing | Richard (Codex) | Deadlines, statuses, triage, draft, submission, and closure rules as pure functions in `core/domain/`. Unit tests driven by Models C and D. The black-box harness in `acceptance/` (takes a base URL and token) and its run instructions. The shared test file with Team 21. |

Team 21 (Aashik, Andrew, Ryan, Conrad) builds an independent implementation of the
same spec. We test their deployment and they test ours.

### Boundaries between areas

- `core/domain/` stays pure: plain values in, plain values or `BadRequest`/`Conflict`/
  `RuleViolation` out. No database, no clock, no Django models. Routes pass in
  `core.clock.now()`.
- Routes and models (Ann) load data, call the domain helpers, persist, write the audit
  entry, and build responses. Business rules don't get re-implemented inside routes.
- Platform code (`cra_service/`, `core/clock.py`, `core/controls.py`, middleware,
  workflows) changes only through a PR Quincy reviews. Never edit
  `.github/workflows/deploy.yml` or `orbit.yml` unless the task says so.
- Changing someone else's area is fine when it unblocks you. Say so in the PR description
  and ask that owner to review.

## Where we are (2026-10-26)

| Item | Status |
|---|---|
| Platform layer: auth, errors, timestamps, clock, reset, logging, CI, deploys | Done, live on Launchpad and Orbit |
| Phase 3 ticket API: intake, get, list (unfiltered), update, triage, audit read, deadlines, unsubmitted statuses | Done. Acceptance suite 55/55 on Launchpad and Orbit (`262fedf`) |
| Course testing interface: `/test/setup`, `/test/report`, and our deployed tester at `/tester` (PR #63) | Done 2026-10-18 |
| Phase 3 report | Was due 2026-10-18. Answers in [reports/phase3.md](reports/phase3.md) |
| Phase 3 pod items carried into Phase 4 | Contract freeze (3.9), Team 21's check of the shared test file (3.10), and Team 21 running their tester against Orbit (3.8) are all still open |
| Phase 4 reporting workflow | Not started. No Phase 4 code on `main` as of 2026-10-26 |
| Console (4.U1 to U4) | Not started. Moved up from Phase 5 (task 5.3) on 2026-10-26 |
| **Phase 4 due date** | **Sunday 2026-11-01** (time of day to confirm) |
| Phase 4 report questions | Not received yet (2026-10-26) |
| Phase 5 due date | Not announced yet |

## Phase 3: deployed service with intake, triage, and deadlines

Goal (Q6.1): a deployed HTTPS service covering REQ-01 to 04, 12 to 14, and 16, passing
AC-01 to 05, 14, 15, and 17 plus OpenAPI response checks, run against **both** teams'
deployments.

| # | Task | Owner | Status |
|---|---|---|---|
| 3.1 | Review PR #7's API and data layer against `openapi.yaml` (see `docs/handoff/ann.md`). Fix verified gaps with focused commits on that branch, not a parallel API. | Ann | Moved after the merge (Quincy's call, 2026-10-17): review the merged code on `main`, and send fixes as PRs |
| 3.1a | Fix the bug found in review (2026-10-17): every PATCH re-checks the *stored* `fix.available_at` against now, so if it's in the future (accepted at create, or the test clock moved back) even a title-only PATCH returns 422. Only check a fix time the request sends. Add PATCH tests for AC-07 cases while there. | Quincy's agent | Done: PR #11 merged into PR #7's branch (Quincy approved) |
| 3.2 | Platform review of PR #7: clock use, transactions and rollback, logging, error precedence, migration safety on Neon. | Quincy | Done 2026-10-17 (with Claude): one bug found, fixed as 3.1a |
| 3.3 | Settle open question Q1 (below) with the pod before 3.4, or document our behavior in `docs/phase3.md`. | Richard, with pod | To do |
| 3.4 | Mark PR #7 ready, merge. Launchpad deploys automatically. Close #5 and #6. | Quincy | Done 2026-10-17: merged as `6548e49`; Launchpad runs it; #5 and #6 auto-closed as merged |
| 3.5 | Run `acceptance/` against Launchpad. Fix anything that fails. | Quincy's agent | Done 2026-10-17: 55/55 passed on Launchpad (`00bda4a`). See `docs/phase3.md`. |
| 3.6 | Launch to Orbit (Actions → Launch to Orbit). Re-run `acceptance/` against Orbit, including the plain-HTTP probe (AC-15). Record the image SHA. | Quincy runs the launch, Richard runs the suite | Done 2026-10-18: Orbit runs `262fedf`; 55/55 passed. See `docs/phase3.md`. |
| 3.7 | Put the Orbit URL in the shared pod file. Send Team 21 the `prod-api-token-team21` token privately. Add or confirm the class registry entry. | Quincy | Done: pod URL and Team 21's token on 2026-10-18; class registry row added 2026-10-17 (Eastern). |
| 3.8 | Get Team 21's base URL and token. Run our suite against them; have them run theirs against Orbit. Team 17 runs suites only against Launchpad and Team 21's deployment, never Orbit (`pod-k-shared` README). Classify every mismatch as our bug, their bug, or a spec gap. | Richard | Half done: our tester passed 55/55 against Team 21 on 2026-10-18 (Eastern). Team 21 hasn't run theirs against Orbit yet; their tester is in `pod-k-shared/team21/` since 2026-10-19. |
| 3.9 | Freeze the `phase-3` operations in `openapi.yaml` with Team 21 (bump `info.version`, note the agreed date). | Ann | To do. The contract and pod spec are now published in `pod-k-shared` (PR #10); freeze that copy, then mirror it here. |
| 3.10 | Start the shared test file with Team 21: Model D inputs and hand-calculated outputs, each checked by the other team. `tests/fixtures/phase3_model_d.json` is a starting point. | Richard (finished by Quincy's agent) | E1 to E8 plus a runner proposed in `pod-k-shared` PR #8 (2026-10-18). Waiting on Team 21's check and approval. |
| 3.11 | Phase 3 report (see [Report work](#report-work)). | Everyone | Done: answers in [reports/phase3.md](reports/phase3.md) |

**Done when** both deployments pass the shared Phase 3 suite and the report records the
runs.

## Phase 4: the full reporting workflow

Goal (Q6.2): updates, report status, all four drafts, submission recording, closure,
listing filters, audit log, reporter confidentiality (REQ-05 to 11, REQ-15). Validated by
AC-06 to 13 and AC-16, plus the first full cross-team run. A scripted incident (submit,
triage, three submissions, close) passes against Team 21's deployment.

**Due Sunday 2026-11-01.** Domain work comes first so the API can wire it in. Agree on
function signatures in the first PR description before building on them.

### Proposed schedule

All dates are proposals from the 2026-10-26 kickoff, not agreed yet. Owners: say if a date
doesn't work for you.

| Day | Domain (Richard) | API (Ann) | Platform and console (Quincy) | Pod |
|---|---|---|---|---|
| Mon 10-26 | Post function signatures for 4.D1 to D5 in a PR description | Start 4.A1 (submission model) | Kickoff; settle console login (4.U1) | Email Team 21: freeze, shared test file, Q2 to Q9, the 404 sequence |
| Tue 10-27 | 4.D1 to D5 PRs open | 4.A1 merged; start 4.A5 filters | 4.U2 pages on existing endpoints | |
| Wed 10-28 | 4.D1 to D5 merged; start 4.T1 | 4.A2 to A4 against Richard's signatures | 4.U2 | Ask Team 21 to answer Q2 to Q9 by today; otherwise we build our proposals and say so in the report |
| Thu 10-29 | 4.T1 acceptance cases | 4.A2 to A5 merged (Launchpad deploys) | 4.P1 reviews; 4.U3 report screens | |
| Fri 10-30 | Run `acceptance/` on Launchpad; fix failures | Fixes; 4.A7 sweep | Launch Orbit (4.P2); draft `pod-k-shared` update | |
| Sat 10-31 | Cross-team run, both directions (4.T4) | 4.A6 Schemathesis | 4.U4 report notes; merge pod update | Needs Team 21's Phase 4 endpoints live |
| Sun 11-01 | Report | Report | Report; submit | |

**Dependencies outside our control:** the cross-team run (4.T4) needs Team 21's Phase 4
endpoints live, and it needs Quincy to launch Orbit first (4.P2). If Team 21 isn't ready by
Saturday, the report records a one-way run and says why.

### Domain Logic and Testing (Richard)

| # | Task | Covers | Status |
|---|---|---|---|
| 4.D1 | `core/domain/drafts.py`: for a report type, ticket fields, ticket ID, and `aware_at`, return the draft `content` and `missing_fields` exactly as Model C says. Never include reporter fields. Unit tests that fill fields one at a time and check all four drafts at each step. | REQ-07, 15; AC-08 | To do |
| 4.D2 | Extend statuses for submitted reports: `submitted` if `submitted_at` ≤ `due_at`, otherwise `submitted_late`. Include the E6 boundary and a clock moved backward. | REQ-05; AC-06 | To do |
| 4.D3 | Submission rule: 409 if the ticket isn't `reportable`, the previous report isn't submitted, or this one is already submitted; 422 if required fields are missing or `submitted_at` isn't between `aware_at` and now. 409 is checked before 422. | REQ-08; AC-09 | To do |
| 4.D4 | Close rule: 409 unless `reportable` with all three reports submitted. | REQ-09; AC-10 | To do |
| 4.D5 | Listing helpers: `next_due_at` (earliest due time among unsubmitted, applicable reports; null if none) and the sort key (nulls last, tie-break per Q2). | REQ-10; AC-11 | To do |
| 4.T1 | Acceptance cases for AC-06 to 12 and AC-16 in `acceptance/cases.py`, running both locally and over HTTP. | | To do |
| 4.T2 | Add Phase 4 cases to the shared test file with Team 21, cross-checked. | | To do |
| 4.T3 | Harness README: running needs `CRA_BASE_URL`, `CRA_API_TOKEN`, and `--allow-reset` (the explicit reset permission). Explain the reset-window etiquette. | Quincy's agent | Done 2026-10-18: `acceptance/README.md`, tested in a clean environment |
| 4.T4 | First full cross-team run, both directions. Resolve disagreements in the spec, not by quietly changing tests. | | Blocked on 4.A1 to 4.A5 |
| 4.T5 | Make the acceptance runner print the report's operation-status table (method and path, requirements, implemented, success and error conformance) from its own results, for the Phase 4 and 5 reports (Q3.1 asks for it each phase). Hand-filled for Phase 3 in `docs/reports/phase3.md`. | Richard | To do |
| 4.T6 | Add automated tests for `GET /tickets/{id}/audit` failure paths: 404 for an unknown ticket and 405 for other methods (`PUT`, `DELETE`). Both checked by hand on 2026-10-17 but not covered by a test. | Richard | To do |

### API and Data (Ann)

| # | Task | Covers | Status |
|---|---|---|---|
| 4.A1 | Submission model and migration: one row per ticket and report type with `submitted_at`, `reference`, the locked `content` snapshot, and the actor. Reset must clear it (anything in the `core` app is cleared automatically). | REQ-08, 18 | To do |
| 4.A2 | `GET /tickets/{id}/reports/{type}`: unknown type → 404. Before submission, build the draft live (4.D1). After submission, return the locked snapshot. | REQ-07, 08, 15; AC-08, 09 | Blocked on 4.D1 |
| 4.A3 | `POST /tickets/{id}/reports/{type}/submission`: `user_advisory` and unknown types → 404. Use 4.D3, store the snapshot, add one `report_submitted` audit entry, return the locked report as a `Draft`. | REQ-05, 08; AC-06, 09 | Blocked on 4.D3 |
| 4.A4 | `POST /tickets/{id}/close`: use 4.D4, set `closed`/`resolved`, add one `closed` audit entry. | REQ-09; AC-10 | Blocked on 4.D4 |
| 4.A5 | Ticket responses use submissions for `obligations.*.status`, `submitted_at`, `reference`, and `next_due_at`. `GET /tickets` supports `state` and `obligation_status` filters (bad values → 400) and the 4.D5 ordering. | REQ-05, 10; AC-06, 11 | Blocked on 4.D2, 4.D5 |
| 4.A6 | Schemathesis against `openapi.yaml`: at least 500 generated malformed requests, no 5xx, every error is problem+json, data unchanged afterward. Runs in CI against the local service and from `acceptance/` against a deployment. | REQ-12; AC-13 | To do |
| 4.A7 | Reporter confidentiality sweep: a unique reporter string appears only in `GET /tickets/{id}`. Check lists, drafts, audit entries, error bodies, and logs. | REQ-15; AC-16 | To do |
| 4.A8 | Keep `openapi.yaml` in sync with Team 21: record every agreed change in the PR and in the file's `info.description`; freeze `phase-4` operations when both teams agree. | | Ongoing |

### Platform (Quincy)

| # | Task | Status |
|---|---|---|
| 4.P1 | Review Phase 4 PRs for platform rules: clock, one transaction per request, rollback on failure, no request bodies in logs, error precedence. | Ongoing |
| 4.P2 | Release each merged increment to Orbit before cross-team runs, and record the image SHA used. | Ongoing |
| 4.P3 | Share the "Open interpretations" table in [platform.md](platform.md#known-limitations) with Team 21 so both services agree on edge cases (reset keeps the clock, 405 precedence, 413 on bodyless routes, and so on). | Done 2026-10-18: covered by the gray-areas tables in `pod-k-shared/team17/TESTING.md` |
| 4.P4 | Automated alerting, promised in Phase 2 (Q7.3) but missing: a Cloud Monitoring alert on 5xx responses (from the request logs) for both deployments. Weigh an uptime check against cost and its effect on spin-up times. | Quincy | To do |
| 4.P5 | Measure AC-18 early: load 1,000 tickets on Launchpad and time 200 mixed requests one at a time (p95 must be at most 1 s), with warm-up handled per `team17/TESTING.md`. Promised in the Phase 3 report (Q7.3) as an early check of the Phase 5 target; the formal run stays task 5.1. | Quincy (hosting), Richard (load script) | To do |

### Console (Quincy)

Our own intake channel (task 5.3), moved up to Phase 4: web pages for a manufacturer's
security team to submit, triage, and follow tickets through to closure. It isn't part of
the shared spec, so it doesn't change the contract or need Team 21's approval. Decided on
2026-10-26 (see [decisions.md](decisions.md)):

- **Who it's for:** the manufacturer's security team (an operations console), not a public
  reporter form.
- **Who builds it:** Quincy. Ann and Richard stay on the graded API and domain work.
- **Where it lives:** server-rendered pages in the same Django service, so there's no second
  deployment. The API token stays on the server and never reaches the browser.
- **Rules it follows:** the same rules as the API, with no business rules in the pages;
  reporter details only on the single-ticket page; the signed-in person's name sent as
  `X-Actor` on every change.

| # | Task | Status |
|---|---|---|
| 4.U1 | Decide how people sign in and how that becomes `X-Actor` (touches auth, so it's a guided decision). Options include per-person Django accounts, a shared password plus a name prompt, or Google sign-in in front of Cloud Run. Not decided. | To do |
| 4.U2 | Pages on the existing endpoints: ticket list (state, report statuses, time until the next deadline), single ticket with audit trail, submit a ticket, triage. | To do |
| 4.U3 | Report pages: each draft with its missing fields highlighted, record a submission, close a ticket. Show "not available yet" until 4.A2 to A4 are live. | Blocked on 4.A2 to A4 |
| 4.U4 | UX notes and screenshots for the Phase 4 report: who it's for, the main flows, and the design decisions. | To do |

## Phase 5: performance, persistence, intake, final version

Goal (Q6.3): REQ-17 and REQ-18, each team's own intake channel, a stable final version.
AC-18 automated, AC-19 by recorded demo, and the full suite (AC-01 to 18) in CI and
against Team 21 before each deadline.

| # | Task | Owner | Status |
|---|---|---|---|
| 5.1 | AC-18 performance on Orbit: load 1,000 tickets, then 200 mixed requests one at a time, p95 ≤ 1 s. Orbit scales to zero and Neon suspends when idle, so warm both with a few requests before measuring and report cold-start numbers separately. If p95 still fails, check query counts on `GET /tickets` first, then consider a temporary minimum instance for the evaluation window. | Quincy (hosting), Richard (load script) | To do |
| 5.2 | AC-19 restart demo: create a ticket with a recorded report, force a new revision (redeploy, or `gcloud run services update` with a harmless env change), read the ticket, report, and audit log back unchanged. Screen-record it. | Quincy | To do |
| 5.3 | Our own intake channel (team's choice, outside the shared spec). If behind, cut it to "clients call `POST /tickets` directly" (Q6.4). | Quincy | Moved up to Phase 4 as the console (4.U1 to U4) on 2026-10-26. Phase 5 finishes it. |
| 5.4 | Full suite (AC-01 to 18) runs in CI on every change, and against Team 21 before each deadline. | Richard | To do |
| 5.5 | Short operations guide: deploy, roll back, rotate tokens, lift the spend cap, read logs. Mostly a trim of [platform.md](platform.md). | Quincy | To do |
| 5.6 | Final spec version agreed with Team 21; final cross-team results recorded. | Ann (spec), Richard (results) | To do |

### If we fall behind

From Q6.4, cut in this order: (1) intake becomes direct API calls, (2) replace the
REQ-17 target with a measured baseline, (3) drop listing filters and ordering (REQ-10).
REQ-01 to 09 and REQ-11 are never cut.

The console (4.U1 to U4) is that intake channel, so it's the first thing cut: if the
Phase 4 API work slips, Quincy pauses the console and helps unblock it.

## Open questions for the pod

Raise each with Team 21 before building on an answer. When one is settled, log it in
[decisions.md](decisions.md), remove it from this table, and update `openapi.yaml` if the
contract changes.

| # | Question | Our current behavior or proposal | Blocks |
|---|---|---|---|
| Q1 | A `not_actively_exploited` or `invalid` triage that also sends `aware_at`: accept and ignore it, store it, or reject it with 400? | PR #7 accepts it and returns `aware_at: null`. | 3.3 |
| Q2 | Listing tie-break when `next_due_at` is equal or null. | Propose `received_at` ascending, then `id`. | 4.D5 |
| Q3 | Drafts for a ticket that never became reportable (`received`, or closed as not reportable): 409? And for a ticket closed as `resolved`, do drafts still read (closed tickets stay readable)? | Propose 409 only for never-reportable tickets; resolved tickets return their locked reports. | 4.A2 |
| Q4 | After a report is submitted, can a later change to `aware_at` or `fix.available_at` move its `due_at`, and so flip `submitted` to `submitted_late`? | Undecided. Status is computed, not stored, so this needs an explicit rule. | 4.D2, 4.A5 |
| Q5 | Must `submitted_at` be no earlier than the previous report's `submitted_at`? | Spec only requires between `aware_at` and now. | 4.D3 |
| Q7 | `POST /tickets` with `fix.available_at` later than now: accept it, or reject it? The field list says "not later than now", but the contract lists no 422 for submit. | Accepted (201). PATCH no longer re-checks a stored fix time (3.1a). Propose adding 422 to submit. | Phase 4 |
| Q8 | Art. 14(2)(c) starts the final-report clock when a corrective **or mitigating** measure is available. We start it only at `fix.available_at` (a fix), so a workaround released first leaves our deadline too late. Redefine `fix.available_at` as the first corrective or mitigating measure? | Proposed: yes, as a wording change to `docs/spec.md` and `openapi.yaml` only. See `docs/reports/risk1-cra-review.md`, Finding 1. | Phase 4 (raise with Team 21 now) |
| Q9 | Art. 14(2)(a) needs Member States only "where applicable" and no product versions, but Model C requires `member_states` and `product.affected_versions` before an early warning can be recorded. Keep it strict, or allow recording with those fields marked unknown? | Undecided. See `docs/reports/risk1-cra-review.md`, Finding 2. | 4.D3 |
| Q6 | A PATCH that changes nothing: still one `updated` audit entry? | Affects AC-12 counts. Propose yes, with an empty `changes` list. | 4.T1 |

## Report work

Each phase report reuses the shared Sections 1 to 6 and updates our own Sections 7 to 9.

- **Phase 4 report:** due with Phase 4 on 2026-11-01. The questions haven't been
  released yet (2026-10-26). Save answers to `docs/reports/phase4.md`, building on
  [reports/phase3.md](reports/phase3.md).

- **Q7 and Q8 are out of date.** The Phase 2 report says FastAPI, SQLite, and
  SQLAlchemy. We built Django + Django Ninja on Cloud Run with Neon Postgres. Rewrite
  Q7.1 (architecture), Q7.2 (decisions), Q7.3 (operations: see [platform.md](platform.md)),
  and Q8.1 (capability decisions, with references) to match.
- **GenAI evidence (Q8.2).** Keep concrete examples of AI output we caught and fixed.
  One is already recorded in `docs/phase3.md`: a test setup that passed on SQLite but
  failed on PostgreSQL in CI (truncating the audit table with deferred foreign-key
  triggers pending).
- **Risks (Q9).** Update the two Phase 2 risks with what we learned (the deadline
  interpretation held for Model D; cross-team compatibility evidence comes from 3.8 and
  4.T4).
- Record for every cross-team run: date, both image SHAs or versions, pass/fail counts,
  and each mismatch's classification.

## Working rules for agents

How agents work with the team (restating the problem first, guide versus delegate, human
approval, the PR template) is in [`AGENTS.md`](../AGENTS.md). These rules add to that and to
[`CLAUDE.md`](../CLAUDE.md).

1. Start from up-to-date `main` (or the branch named in the task) on a new branch. One
   task per PR, and reference its task number (for example, "4.D1") in the PR title.
   Never push to `main`.
2. Before opening a PR, run `pytest -q`, `ruff check . && ruff format --check .`, and
   `python manage.py makemigrations --check --dry-run` against local Postgres
   (`docker compose up -d`). CI uses Linux, Python 3.12, and Postgres 18; SQLite passing
   isn't enough.
3. Expected values in tests come from [spec.md](spec.md) (Models C and D, the AC table)
   or hand calculation, never from running the code under test.
4. Never point `acceptance/` at Orbit or Team 21 without a booked window. It resets the
   whole deployment. Never paste tokens into a prompt, a commit, or a PR.
5. If the spec is ambiguous, don't pick an answer silently. Add it to
   [Open questions](#open-questions-for-the-pod) and tell the owner.
6. When you finish a task, update its status here in the same PR.
7. If your PR settles a question or changes scope, the contract, or ownership, add an
   entry to [decisions.md](decisions.md) in the same PR.
