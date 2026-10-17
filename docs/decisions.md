# Decision log

Decisions that change scope, the contract, the architecture, or who does what, newest
first. The [plan](plan.md) tracks tasks. This file records why things are the way they
are, so nobody (human or agent) re-argues a settled question.

**Adding an entry:** add it at the top in the same PR as the change it explains. Give the
date, who decided (us, or the pod with Team 21), the decision, and the reason. When an
[open question](plan.md#open-questions-for-the-pod) is settled, log it here and remove
it from the plan's table. Never edit an old entry. If a decision is reversed, add a new
entry that says so.

| Date | Decided by | Decision | Why |
|---|---|---|---|
| 2026-10-17 | Team 17 | PR #7 is the Phase 3 integration path. PRs #5 and #6 are contained in it and close when it merges. Ann reviews and takes ownership of its API and data layer rather than rebuilding it. | Richard built a minimal API layer so Phase 3 could be integrated and tested while Ann's work was pending. One branch avoids duplicate APIs. |
| 2026-10-17 | Team 17 | `docs/plan.md` is the task board and `docs/spec.md` is the in-repo copy of the Phase 2 spec. Every agent reads them before starting a task (PR #8). | Teammates use different agents (Claude Code, Codex), and none of them can read the Phase 2 PDF. |
| 2026-10-05 | Team 17 | Each client gets its own API token (Team 17, Team 21, staff), and logs record which client called. | A token can be revoked for one client without affecting the others, and logs show who ran what. |
| 2026-10-05 | Team 17 | Platform edge cases the contract leaves open (reset keeps the fixed clock, 405 after 401, 413 on every route, and others) are settled as listed in [platform.md](platform.md#known-limitations). | `openapi.yaml` is silent on them. Still to share with Team 21 (plan task 4.P3). |
| 2026-10-04 | Team 17 | Two deployments: Launchpad (`team17-dev`, deploys on every merge to `main`) and Orbit (`team17-prod`, manual launch, used for evaluation). | Our own testing never disturbs the deployment Team 21 and the instructors test against. |
| 2026-10-04 | Team 17 | Django + Django Ninja on Cloud Run with Neon Postgres, replacing the FastAPI, SQLite, and SQLAlchemy plan in the Phase 2 report (Q8.1). | The team chose Django (reason still to record). Ninja keeps FastAPI-style typed schemas on top of Django. Cloud Run containers have no persistent disk, so SQLite wouldn't survive a restart (REQ-18), which means hosted Postgres. The Phase 3 report must update Q7 and Q8. |
| 2026-09-25 | Pod | Phase 2 spec agreed: shared scope, REQ-01 to 18, Models A to D, AC-01 to 19, and the interface. Recorded in [spec.md](spec.md). | Both teams implement it independently and test each other's deployments. |
| 2026-09-25 | Pod | SBOM matching and integration with an existing ticketing product were dropped. Severe incidents (Art. 14(3)-(4)) are out of scope. | Unreliable component identifiers; cross-team tests would depend on outside accounts; keeps one deadline model. |
