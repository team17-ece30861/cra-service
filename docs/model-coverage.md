# Phase 5 model coverage

**Design version:** `team17-phase5-design-v1`. Richard approved the 44-requirement
baseline and counting rules on 2026-11-19 for local implementation. This is not a
claim that every requirement is implemented/evaluated, that teammates approved a
release, or that the changes have reached Launchpad or Orbit.

The source design is Models A-D, the delivered architecture, the pod requirements
in [spec.md](spec.md), and the Phase 5 targets in [plan.md](plan.md). Course testing
interface v2 adds own-system model coverage. It does not replace the pod CRA API
or authorize changes to unresolved Q7/Q8/Q9 behavior.

## Inventory and executable scenario mapping

The [manifest](../acceptance/model_requirements.json) freezes **44 requirements and
266 required scenarios**. Each scenario has a stable ID and either an exact
collected remote-test node ID or a null binding for an unimplemented/CI-only check.
The 141 current bindings are checkpoint candidates in the existing portable
tests, not 141 passing requirements. Parameter values and wrapper classes are
explicit; no fuzzy matching or AC-name inference supplies model evidence.

The table's last column is bound scenarios / required scenarios. Unbound scenarios
stay in the inventory and denominator. CI-only checks, recorded demos, performance
runs from another session, and source inspection are not current-suite model
coverage.

| ID | Design requirement | Bound / required scenarios |
|---|---|---|
| A-01 | Intake produces distinct IDs in `received`, with the fixed service receipt time and no awareness time. | 1/1 |
| A-02 | Valid exploitation triage enters `reportable`; missing awareness/reason, future awareness, and retriage are rejected without changing the ticket. | 9/9 |
| A-03 | Both non-exploitation decisions close the ticket with the matching resolution; edits, regulatory submissions, and resolution are rejected, while the detail remains readable. | 10/10 |
| A-04 | Allowed detail edits preserve unspecified nested fields; awareness edits require a reason and reportable state, reject future awareness and fix times, and immediately recalculate deadlines without partial changes. | 0/7 |
| A-05 | Regulatory reports record only while reportable, in predecessor order, once per type; missing fields and an out-of-interval timestamp reject recording without changes. | 30/30 |
| A-06 | Resolution succeeds only for a reportable ticket with all three report types recorded; zero, one, or two recorded reports and never-reportable tickets cannot close as resolved. | 7/7 |
| A-07 | A resolved ticket is read-only for every declared change operation and retains readable report snapshots. | 8/8 |
| A-08 | Every successful ticket change records exact sequence, actor, time, action, reason and allowed old/new field values; failures add nothing and audit entries cannot be edited/deleted. A real edit adds an entry and a no-op does not. | 0/9 |
| B-01 | All obligations are `not_applicable` before reportable triage and after either not-reportable closure, with no due times in the closed case. | 3/3 |
| B-02 | An unrecorded final report awaits a fix; adding a fix creates its deadline/status; clearing a fix returns an unrecorded report to `awaiting_fix`, including from pending and overdue. | 0/5 |
| B-03 | An unrecorded report is pending at its exact due time and overdue one second later; moving the clock back can restore pending. | 0/3 |
| B-04 | Recorded on-time/late status compares submitted time to the deadline, including equality; moving now backward does not change that recorded status. Ticket, list and draft metadata agree. | 4/4 |
| B-05 | Editing a deadline can move a recorded report between submitted and submitted-late; a recorded final report with its fix cleared follows the documented submitted fallback. | 0/3 |
| C-01 | The complete content of all four draft types matches Model C's allowlists, including advisory optional fields and excluding reporter fields. | 4/4 |
| C-02 | Missing required fields update correctly as fields are filled or cleared; empty required values are still missing, and optional values do not become requirements. | 0/4 |
| C-03 | Reads do not mutate tickets/audit; a recorded regulatory report keeps locked content after edits, while unrecorded drafts use current fields. | 9/9 |
| C-04 | Drafts are unavailable for never-reportable tickets; the advisory has no regulatory deadline/submission, cannot be recorded, and remains readable after resolution. | 15/15 |
| D-01 | E1: Friday awareness produces the specified overdue early-warning and pending notification dates at Monday triage. | 1/1 |
| D-02 | E2: Monday awareness produces the specified +24h and +72h deadlines. | 1/1 |
| D-03 | E3: awareness after receipt starts deadlines from awareness, not receipt. | 1/1 |
| D-04 | E4: a later fix produces exactly the specified +14-day UTC final-report deadline. | 1/1 |
| D-05 | E5: a fix before awareness starts the final-report deadline from awareness as the pod example specifies. | 1/1 |
| D-06 | E6: pending at the exact due time, overdue one second later. | 2/2 |
| D-07 | E7: the offset input normalizes to the specified whole-second UTC time/deadline; fractional input truncates and malformed timestamps are rejected without changes. | 5/5 |
| D-08 | E8: awareness one second in the future returns 422, preserving received state and its lack of deadlines. | 1/1 |
| X-01 | Ticket/list/draft status metadata agree; filters select exact tickets; urgency orders nearest unmet deadline first, nulls last, then receipt time and ID. | 0/5 |
| X-02 | The project API requires valid bearer auth except public health; the deployed HTTP endpoint refuses or redirects to HTTPS without sending credentials. | 28/28 |
| X-03 | All five ticket-write operations require a valid X-Actor and successful changes record that actor without reporter leakage. | 0/6 |
| X-04 | For combined faults, errors follow 401, 413, 404, 400, 409, 422 and match the contract without changing application state. | 0/7 |
| X-05 | A failure after saving state/snapshots, during audit or rendering, rolls the whole write back and leaves no audit gap. | 0/5 |
| X-06 | Domain helpers remain independent of Django/database/clock reads, accept caller-supplied time, and do not mutate their inputs/results. | 0/3 |
| X-07 | Reporter name/contact appear only in single-ticket detail and never in other HTTP responses or application logs. | 0/2 |
| X-08 | The console uses its own sign-in session, does not unlock the bearer-token API, reuses ticket rules, records the signed-in actor, and rolls back rejected console changes. | 0/5 |
| X-09 | Reset clears tickets/reports/audit but keeps test sessions and the fixed clock; clock reads remain fixed until changed/released; invalid clock input changes nothing. | 0/8 |
| X-10 | Across all timestamp-bearing project and clock responses, accepted RFC 3339 offsets normalize to UTC whole seconds with truncation, and invalid required timestamps are rejected without changes. Include receipt/awareness/fix/submission times, deadlines and audit times, not just E7's awareness field. | 0/8 |
| I-01 | AC-02: missing title, invalid source, client-set receipt time and malformed JSON are rejected with the prescribed 400 errors; a body above 65,536 bytes returns 413. Field-specific errors identify the bad field where applicable, and rejected intake changes no application data. | 0/6 |
| I-02 | AC-13: send at least 500 malformed requests generated from the agreed OpenAPI document; receive no 5xx, validate each error against the specified format, and verify application data is unchanged. | 0/5 |
| P-01 | AC-18: with 1,000 tickets, 200 sequential mixed requests meet the p95 <= 1 s target, with warm-up and cold-start results reported separately under an agreed protocol. | 0/1 |
| P-02 | AC-19: ticket, recorded-report content and audit survive a real service restart. | 0/1 |
| T-01 | Setup creates a unique nonempty session, passes the same ID to the target, waits for preparation, forwards setup errors, and leaves no runnable session on failure. Duplicate target IDs conflict. | 0/6 |
| T-02 | A prepared session runs once, waits for completion, rejects reuse, and exposes the same immutable stored report; invalid requests do not consume it and pending report lookups return 409. | 0/6 |
| T-03 | Every planned test appears once with nonempty ID/message and the right pass/fail/error/skip meaning; aborts retain outcomes, and errors distinguish tester/system/communication/unknown. A finished suite returns 200 even with target failures; a tester abort returns 500 and retains a report. | 0/6 |
| T-04 | Every suite report carries valid code/component/system measures; same-team reports additionally carry this model measure with the approved version/mapping, while cross-team reports omit it. Counts are bounded or both null with a reason; coverage is not pass rate. | 0/7 |
| T-05 | Distinct tester sessions cannot unintentionally reset, change the clock, or overwrite the target state/coverage of an active run. The agreed policy protects preparation, execution, coverage retrieval and cleanup, including abort/lost-response paths, and documents recovery after interruptions. | 0/7 |

## What counts

A `model_scenario` context wraps a particular oracle's assertions after the target
values are available. Completing the comparisons records a boolean evaluation;
an `AssertionError` records a failed comparison and is re-raised unchanged.
Timeouts, setup failures, other exceptions and unexecuted work do not invent
evaluations. Checkpoint blocks do not make HTTP calls. Earlier failures do not
supply evidence for later checkpoints.

Multi-comparison groups eagerly compute every boolean predicate before their
aggregate assertion; an early failed comparison cannot credit values never read.
Empty or unevaluated predicate groups invalidate the measure. Status-only
checkpoints surround the actual status comparison in `Service.expect`, so a
wrong-but-evaluable 200/400 can record failure, but transport failures and an
unexpected 5xx do not pretend the design oracle ran. Snapshot-locking checkpoints
for all three report types execute after a real product edit, not just immediately
after recording. Optimized Python invalidates the collector rather than counting
assertions removed by `-O`.

The pytest call-phase hook binds the recorder to the actual test node ID.
Fixture setup/teardown cannot add model evidence. Emitting from an unrelated test,
a local CI wrapper, or an unbound scenario invalidates the measure rather than
inflating it. Evidence contains scenario IDs and booleans only, not target bodies,
tokens, actors or resource IDs.

A requirement counts once only when every scenario in its frozen list was
evaluated in this session. A failed evaluated comparison still counts as coverage,
not correctness. The existing operation-conformance table remains stricter:
a failed/skipped/incomplete test cannot establish passing operation evidence.

Filtering, a missing test or an abort does not shrink the total from 44. Duplicates
do not increase it. An available collector with no reached scenarios reports 0/44;
missing, corrupt, wrong-version or invalid evidence reports two null counts with
a reason. The manifest's semantic checksum pins its contents; changing requirements,
scenario obligations or bindings requires a deliberate design-version update,
new checksum, reviewed tests and updated documentation.

## Reports, aborts and configuration

The deployed tester adds `coverage.model` only when the target matches an explicit
own-system base URL. The existing code/component/system fields and project API are
unchanged. A different team's target omits model, even when it shares a host or a
token configuration with ours.

Configuration uses nonsecret settings:

- `TESTER_OWN_SYSTEM_URLS`: a JSON list of complete system base URLs. Defaults are
  the two Team 17 bases documented in README (Launchpad and Orbit). Confirm those
  deployment identities with Quincy before release. Scheme, nondefault port and
  base path matter; hostnames alone are insufficient. This setting does not alter
  allowed targets, credentials or authentication.
- `TESTER_MODEL_MAPPING_URL`: the actual published, preferably commit-pinned URL
  of this version's mapping. It defaults to empty while this change is local.
  Until published/configured, own reports include model with null counts and
  explicitly say the mapping is unavailable. Do not use a local Windows path or
  claim a future GitHub URL already exists. The link must be accessible to course
  staff and podmates; use a reviewed public shared-repo copy if the service repo
  is private, and publish the matching scenario manifest with it.

The runner writes a separate `--model-progress FILE` JSON Lines journal in its
temporary directory. Its version header precedes tests, and each reached oracle
is flushed before the test continues. An abort can recover those evaluations even
if ordinary per-test teardown/progress or the final JSON report is incomplete.
A complete invalid record or an explicitly failed collector makes coverage
unavailable. A trailing incomplete write is not an evaluation.

Standalone JSON additionally carries per-result `model_evidence` and the
`model_evidence_version` / `model_evidence_available` run metadata. These are the
evidence channel, not a claim that every standalone target belongs to Team 17.
The course report contains only the normal covered/total/basis model measure.

Report storage and retrieval remain unchanged: run waits for the suite and stores
its report, normal completion returns 200 even with failing tests, an abort returns
500 with the available report retained, and GET report does not rerun the suite.
Cross-session interference, cleanup and stale-running recovery remain Quincy's
separate task 5.8, not silently solved by this collector.

## Scope and release gates

This change implements the collector and existing bound checkpoint instrumentation.
It does not implement the unbound AC-07/fuzz/performance/restart/console/architecture
checks or the separate operation-table review follow-ups. Counts may legitimately
be partial; do not hide those gaps to improve them.

Before a release: obtain independent posted review and current CI; have Quincy
confirm the self-target registry and published mapping URL; validate on Launchpad
with explicit reset permission; follow Quincy's Orbit launch and shared-copy
publication process. Update `docs/interface/tester.yaml` and tests together.
Refresh the portable tester copy with the new Python module and JSON manifest.
No shared-target run or deployment is authorized by this document.

## Local verification on 2026-11-19

Selected domain/API/tester/controls regression passed 1,262 tests with four
existing PostgreSQL-only row-lock skips, including 89 new model tests. The nested
real-pytest/in-process-Django portable suite passed 221 tests and skipped its one
HTTPS-only probe: 140 distinct scenarios were evaluated, completing 19/44 design
requirements. Its mapping URL was explicitly synthetic test data. These are not
deployed HTTP, source-code coverage or feature-completion results.

Independent local review identified four counting defects across two passes;
negative probes and eager/status/post-edit oracles corrected them. Final re-review
found no new actionable issue. Lint/format, Django and migration checks pass.
Posted PR review, Linux/PostgreSQL CI, accessible mapping publication/configuration
and authorized deployed validation remain release gates.

## Traceability to every pod requirement

This is a complete identifier crosswalk, **not a statement that every requirement
is delivered or tested**. Owners below are verification/follow-up responsibilities,
not authorship attribution. Existing feature ownership and review rules still
apply. Missing checks remain missing even though an identifier has a row.

| Pod requirement | Design rows | Verification / follow-up owner | Evidence state and remaining gap |
|---|---|---|---|
| REQ-01 | A-01, I-01 | Richard tests; Ann API follow-up | Existing happy-path/intake rejection candidates; strengthen rejected-input preservation and run again. |
| REQ-02 | A-02, D-01, D-02, D-03, D-08 | Richard with Ann for API changes | Collector and triage/Model D checkpoints implemented locally; no deployed Phase 5 measurement claimed. |
| REQ-03 | A-03, B-01 | Richard tests; Ann API follow-up | Closed-not-reportable checkpoints exist for both decisions; no fresh deployed run claimed. |
| REQ-04 | D-01, D-02, D-03, D-04, D-05, B-02, B-05 | Richard domain/tests; Ann and pod for Q8 | Deadline candidates exist; fix-clearing/transition checks and the workaround wording decision remain separate. |
| REQ-05 | B-01, B-02, B-03, B-04, B-05, X-01 | Richard tests; Ann API/status follow-up | Several transition branches are partial or CI-only; do not infer complete status coverage. |
| REQ-06 | A-04, A-07, A-08, B-05 | Richard HTTP tests; Ann API follow-up | AC-07 HTTP and full awareness/fix-edit oracles are pending. |
| REQ-07 | C-01, C-02, C-03, C-04 | Richard | Existing four-draft candidates; clear/empty-field remote checks remain partial. |
| REQ-08 | A-05, C-02, C-03, C-04 | Richard; Ann and pod for Q9 | Existing submission candidates; keep unresolved contract changes and the multiple-errors question explicit. |
| REQ-09 | A-03, A-06, A-07 | Richard | Existing closure/state/read candidates; fresh evaluation and separate internal rollback evidence needed. |
| REQ-10 | X-01 | Richard tests; Ann listing follow-up | Existing filtering/urgency candidates; exact final ID tie-break check pending. |
| REQ-11 | A-08, X-05, X-07 | Richard tests; Ann API follow-up; Quincy platform review | Sequence/no-op candidates exist; complete old/new-value and mid-write rollback evidence remain partial/CI-only. |
| REQ-12 | I-01, I-02, A-02, A-04, A-05, A-06, X-04, X-05 | Ann generation/API; Richard regression; Quincy platform | Explicit AC-02/AC-13 rows now present; malformed-input, route-error and state-preservation matrices are not complete. |
| REQ-13 | A-01, D-07, X-10 | Richard tests; Quincy timestamp/platform follow-up | E7 and submission-time candidates exist; global timestamp field/route matrix pending. |
| REQ-14 | X-02, X-03, X-08 | Quincy platform; Richard tests | API auth/HTTPS candidates exist; actor-route cases and own console/interface checks need separate evidence. |
| REQ-15 | C-01, X-07 | Richard HTTP tests; Ann privacy/API follow-up; Quincy logs | HTTP privacy candidates exist; log inspection remains CI-only, not remote-suite evidence. |
| REQ-16 | X-09, T-01, T-02, T-05 | Quincy controls/session safety; Richard harness | Reset/fixed-clock candidates exist; clock release, session retention and cross-session interference checks pending. |
| REQ-17 | P-01 | Richard script; Quincy deployed performance | Protocol approval, script and measured performance evidence are pending. |
| REQ-18 | P-02 | Quincy demo; Richard records results | Authorized restart demonstration and exact before/after evidence pending; manual evidence is not suite coverage. |

## Traceability to every pod acceptance criterion

Exact test/scenario bindings and remaining null bindings are in the executable
manifest linked above. Availability in this crosswalk is not a passing deployed
result. The expected behavior always comes from the pod spec/contract, not this
crosswalk; local regression and deployed validation remain different evidence.

| Acceptance criterion | Pod requirement(s) | Design rows | Owner and evidence gap |
|---|---|---|---|
| AC-01 | REQ-01, REQ-13 | A-01, X-10 | Richard: existing intake candidates; field-wide time checking is broader and partial. |
| AC-02 | REQ-01, REQ-12 | I-01 | Richard tests/Ann API: five basic input candidates exist; strengthen no-change checks. |
| AC-03 | REQ-02, REQ-04 | A-02, D-01, D-02, D-03, D-04, D-05 | Richard: exact E1-E5 candidates exist. |
| AC-04 | REQ-02 | A-02, D-08 | Richard: missing/future awareness, missing reason and retriage candidates exist. |
| AC-05 | REQ-03, REQ-09 | A-03, B-01 | Richard: not-reportable closure/read/rejected-edit candidates exist. |
| AC-06 | REQ-05 | B-02, B-03, B-04, D-06 | Richard: exact-boundary and submitted-status candidates exist; broader reverse/clearing transitions remain partial. |
| AC-07 | REQ-06 | A-04, A-08 | Richard: CI integration candidates exist; dedicated deployed HTTP scenarios and full audit assertions pending. |
| AC-08 | REQ-07, REQ-15 | C-01, C-02, X-07 | Richard: fill/read-all-four candidates exist; broader empty/clear scenarios and logs are separate gaps. |
| AC-09 | REQ-08 | A-05, C-02, C-03, C-04 | Richard: recording/order/locking candidates exist; setup must distinguish missing predecessor from missing fix, and the all-problems-in-422 oracle is unresolved. |
| AC-10 | REQ-09 | A-06, A-07 | Richard: outstanding-report and successful-resolution candidates exist. |
| AC-11 | REQ-10 | X-01 | Richard tests/Ann listing: exact filters/order candidates exist; add equal-receipt ID tie-break coverage. |
| AC-12 | REQ-11 | A-08, X-05 | Richard: lifecycle/immutable-audit candidates exist; full old/new and internal-failure proofs need stronger or separate bindings. |
| AC-13 | REQ-12 | I-02 | Ann generation, Richard integration, Quincy deployed coordination: our 500-malformed-request check pending. |
| AC-14 | REQ-13 | D-07, X-10 | Richard: E7/bad timestamp/truncation candidates exist; global timestamp consistency is broader. |
| AC-15 | REQ-14 | X-02, X-03 | Richard tests/Quincy platform: auth/HTTPS candidates exist; remaining actor-route cases pending. |
| AC-16 | REQ-15 | C-01, X-07 | Richard tests/Ann privacy: HTTP lifecycle candidates exist; logs require separate accessible evidence. |
| AC-17 | REQ-16 | X-09 | Richard tests/Quincy controls: reset/fixed-clock candidates exist; successful release/session-retention extensions pending. |
| AC-18 | REQ-17 | P-01 | Richard script/Quincy run: agreed load protocol and measured result pending. |
| AC-19 | REQ-18 | P-02 | Quincy restart demo/Richard evidence: recorded before/after result pending, separate from model-suite counting. |

The console/internal-architecture and course-interface rows also trace to the
team design and course v2. They do not invent additional pod REQ/AC numbers. The
remaining delivery tasks and report work are tracked separately in docs/plan.md.
