# Models as delivered (Phase 4)

The Phase 2 models (Sections 3.2 and 7.1), redrawn to match the system as actually
delivered at the end of Phase 4. Each `.mmd` file is the Mermaid source; each `.png` is its
render (mermaid-cli 11.4.2), checked by eye for overlaps and against the code for accuracy.

**Notation, shared by all three:** rounded boxes are states; plain boxes are components.
Everything drawn exists in the delivered system (the Phase 3 versions drew Phase 4 parts
dashed). Every diagram has a legend. An independent AI session (one that didn't draw them)
checked all three against the code on 2026-11-01; its findings were fixed before merge.

| Model | Changed in Phase 4 | What changed and why | Files |
|---|---|---|---|
| A. Ticket lifecycle (state machine) | Yes | Recording the three reports and closing a reportable ticket as `resolved` are now delivered, so they're solid. The reportable state lists what can be read and recorded (all four drafts; the three reports once each, in order), and each closed state says whether drafts are readable (Q3). | `model-a-ticket-lifecycle.*` |
| B. Report status (state machine) | Yes | `submitted` and `submitted_late` are delivered. Adds `overdue` → `submitted` (a report recorded with a `submitted_at` at or before its due time) and the two-way `submitted` ↔ `submitted_late` transitions when a later edit moves the deadline (Q4, agreed with Team 21); Phase 2 drew the submitted states as final. Also adds the transitions for three cases an independent check found reachable but undrawn: a report can already be `overdue` at triage (Model D E1), a fix given at intake skips `awaiting_fix`, and clearing the fix sends an unrecorded final report back to `awaiting_fix`. | `model-b-report-status.*` |
| C. Required fields per draft (table) | No | Delivered exactly as specified; the tester checks every draft against the table. The early-warning fields are still stricter than Art. 14(2)(a); the pod agreed to allow "unknown" (Q9), which needs a contract change in Phase 5. | `docs/spec.md` |
| D. Deadline examples (table) | No | The delivered service reproduces E1 to E8 exactly (shared test file, `pod-k-shared/tests/`, checked by Team 21). | `docs/spec.md` |
| Section 7.1 architecture and data flow (component diagram) | Yes | Adds what Phase 4 delivered: draft, submission and close routes, the Model C draft builder and the submission, close and listing rules, the `ReportSubmission` table, and the console (`/console/`, Django sign-in instead of the bearer token, calling the ticket routes in-process). Also adds the course's cross-team testing interface (test setup and report, the deployed tester, its subprocess, and their session tables), which existed since Phase 3 but was missing from the Phase 3 drawing. Now has a legend. | `architecture.*` |

To re-render after an edit: `npx -p @mermaid-js/mermaid-cli@11.4.2 mmdc -i <file>.mmd -o <file>.png -b white -s 2`,
then look at the image before committing.
