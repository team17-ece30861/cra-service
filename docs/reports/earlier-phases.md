# Earlier phases: what Team 17 said, and what's changed

A Markdown summary of Team 17's own sections from the Phase 1 and Phase 2 reports, for
agents writing later reports. The shared pod spec (Phase 2, Sections 2 to 6) is in
[`docs/spec.md`](../spec.md). The original PDFs are in [`source/`](source/).

## Phase 2, Team 17's sections (submitted 2026-09-27)

### Q7.1 Architecture (as planned)

A layered single web service. Requests come in through the common REST API, then pass
authentication and validation. Application logic is split into a deadline calculator, a
report draft generator, an audit log manager, and a ticket/state manager. A persistent
database stores tickets, reports, and audit logs. Test controls (`/test/reset`,
`/test/clock`) reset data and override the current time. Framework, database, and hosting
were undecided at the time.

**Now:** built as planned, with Django + Django Ninja on Cloud Run and Neon Postgres. Pure
domain logic lives in `core/domain/`, routes in `core/tickets.py`, and the platform in
`cra_service/`. Report drafts don't exist yet (Phase 4).

### Q7.2 Design decisions

1. **Single service with internal modules**, not microservices: less deployment and
   communication complexity; supports REQ-17 and easier cross-team testing. **Held.**
2. **Persistent relational database**, not in-memory or JSON files: supports REQ-10, 11,
   and 18. **Held** (Postgres rather than the SQLite named in Q8.1).

### Q7.3 Operation and observability

Planned: one HTTPS service with a persistent relational database; bearer tokens; secrets
in environment variables or the platform's secret manager; logs for requests, validation
and auth failures, state changes, and server errors; monitoring of status codes, latency,
and availability; a separate development deployment and an evaluation deployment; logs
record ticket IDs, never request bodies (REQ-15).

**Now:** all done as planned. Launchpad is the development deployment and Orbit the
evaluation one. Secrets are in Google Secret Manager, with one API token per client. See
[`docs/platform.md`](../platform.md).

### Q7.4 Validation strategy

Planned: prototype the core lifecycle (create, triage, deadlines) against the Phase 2
cases; static checks (schema validation, code quality) before integration; automated tests
for endpoints, invalid inputs, state transitions, and deadline boundaries on every push;
write a regression test before each fix.

**Now:** done as planned. CI runs lint, migration checks, and the full test suite on every
PR, and the acceptance suite checks every response against `openapi.yaml`. The PATCH
fix-time bug (PR #11) followed the regression-test-first rule.

### Q8.1 Capability decisions: superseded

Phase 2 said **FastAPI** [6] for the API and **SQLite with SQLAlchemy** [7], [8] for
storage. We built **Django + Django Ninja** on **Google Cloud Run** with **Neon Postgres**
instead. See [`docs/decisions.md`](../decisions.md) for why (2026-10-04 entry). The Phase 3
report's Q8 and its references need rewriting to match.

### Q8.2 GenAI use

Planned: ChatGPT and Claude Code for scaffolding, test ideas, debugging, review, and
documentation. GenAI isn't part of the running system and makes no reporting or compliance
decisions. All AI output is reviewed by a team member and validated by the acceptance
tests. Only simulated data goes to AI services.

**Now:** Claude Code (Quincy) and Codex (Richard and Ann). The team workflow in
[`AGENTS.md`](../../AGENTS.md) adds human approval for every code PR. Recorded examples of
AI output caught and fixed: the PostgreSQL test-transaction failure (`docs/phase3.md`), the
PATCH fix-time bug (PR #11), and two testing-guide claims that held locally but not on the
deployed stack (`pod-k-shared` PR #6).

### Q9.1 Priority risks

1. **Our reading of awareness time, fix availability, the 14-day final report, and the
   final report's contents might not match the CRA.** Planned investigation: *during
   Phase 3, Team 17 reviews the relevant CRA provisions against Models C and D and writes
   up whether the interpretation is unambiguous.* Fallback: list our assumptions.
   **Status: not done yet**, as far as the repo shows.
2. **Cross-team compatibility.** Planned check: the pod runs the shared suite against both
   deployments at the end of Phase 3, then fully in Phase 4. **Status: our suite passes
   against us; Team 21's runs are pending.**

### Q9.2 Risks needing pod agreement

Risk 1, if it materializes, would change shared scope and requirements; the pod decides by
Phase 4.

### References used in Phase 2

[1] CRA, Regulation (EU) 2024/2847. [2] RFC 9110. [3] RFC 9457. [4] RFC 3339. [5] TLP 2.0
(FIRST). [6] FastAPI docs. [7] SQLite "About". [8] SQLAlchemy ORM 2.1.1.

## Phase 1 (submitted 2026-09-13)

- **Focus:** post-release vulnerability handling (Art. 13, Annex I Part II) and reporting
  (Art. 14).
- **Team 17's concepts:** the *CRA Reporting Manager* (Article 14 deadlines, drafts, audit
  log; this became the project) and the *Release Component Index* (SBOM-to-release
  lookup; dropped in Phase 2 because component identifiers don't match reliably).
- **Pod finding:** the two teams read "becoming aware" differently. Team 17 started the
  clock when a person first sees a report; Team 21 started it once exploitation is
  confirmed. Phase 2 resolved this by having a person record the awareness time at triage
  (REQ-02), with the system never inferring it.
- **Ambiguity noted:** "without delay" for remediation has no fixed deadline, so the
  system tracks times but doesn't judge compliance on its own.
