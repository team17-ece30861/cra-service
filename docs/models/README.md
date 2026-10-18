# Models as delivered (Phase 3)

The Phase 2 models (Sections 3.2 and 7.1), redrawn to match the system as actually
delivered in Phase 3. Each `.mmd` file is the Mermaid source; each `.png` is its render
(mermaid-cli 11.4.2), checked by eye for overlaps and against the code for accuracy.

**Notation, shared by all three:** rounded boxes are states or components that exist
today; dashed boxes and dotted arrows are specified in the pod spec but arrive in Phase 4.
Every diagram has a legend.

| Model | Changed | What changed and why | Files |
|---|---|---|---|
| A. Ticket lifecycle (state machine) | Yes | Drawn as delivered: submit, both triage outcomes, and updates are implemented; recording report submissions and closing a reportable ticket as `resolved` are specified but arrive in Phase 4, so they're dotted. Updates are listed inside each state instead of as self-loops. | `model-a-ticket-lifecycle.*` |
| B. Report status (state machine) | Yes | `not_applicable`, `awaiting_fix`, `pending`, and `overdue` are delivered and recalculated on every read; `submitted` and `submitted_late` need submission recording (Phase 4). Adds `awaiting_fix` → `overdue`, which the delivered system does when a fix is recorded after its 14-day due time has already passed; the Phase 2 drawing only showed `awaiting_fix` → `pending`. | `model-b-report-status.*` |
| C. Required fields per draft (table) | No | Drafts aren't built yet (Phase 4). The risk 1 CRA review flagged the early-warning required fields as stricter than Art. 14(2)(a); that's under evaluation, not changed. | `docs/spec.md` |
| D. Deadline examples (table) | No | The delivered service reproduces E1 to E8 exactly (shared test file, `pod-k-shared/tests/`). | `docs/spec.md` |
| Section 7.1 architecture and data flow (component diagram) | Yes | Removed the Report Draft Generator and stored reports (neither exists until Phase 4). Audit logging is part of the ticket routes, not a separate manager. Added the platform middleware (token check, 64 KB limit, one transaction per write) and the service clock. Names the actual stack (Cloud Run, Django Ninja, Neon Postgres), which Phase 2 left undecided. | `architecture.*` |

To re-render after an edit: `npx -p @mermaid-js/mermaid-cli@11.4.2 mmdc -i <file>.mmd -o <file>.png -b white -s 2`,
then look at the image before committing.
