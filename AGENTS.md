# How we work with agents

Team 17 uses AI agents (Claude Code, Codex) for as much of the building as we can, and
the humans stay in control: people make the decisions and approve what ships. This file
applies to every agent working in this repository. "The person" means the teammate
driving you.

Read these before starting any task:

1. [`CLAUDE.md`](CLAUDE.md): repository rules (clock, UTC, errors, X-Actor, logging).
   They apply to every agent, not only Claude.
2. [`docs/plan.md`](docs/plan.md): who owns what, current status, the task list.
3. [`docs/spec.md`](docs/spec.md) and [`openapi.yaml`](openapi.yaml): the agreed behavior
   and the API contract. [`docs/decisions.md`](docs/decisions.md): what's already settled.
4. [`docs/handoff/`](docs/handoff/): one file per teammate (`quincy.md`, `ann.md`,
   `richard.md`). Read all three, so you know what the others are in the middle of and
   what they're waiting on.

## Before building anything

- **Restate the problem first.** Before planning, tell the person in plain English what
  the task is, what the code does today, where the request looks off, and how risky the
  change is. Tasks in the plan (or written by another AI) are a starting point, not a spec.
- **Guide or delegate, by risk.** For anything non-trivial, ask whether the person wants to
  work through the decisions with you (guide) or hand them to you (delegate). Recommend one:
  - *Guide* anything that touches `openapi.yaml` or spec behavior, migrations, auth, errors,
    middleware, deploy workflows, or what Team 21 can observe.
  - *Delegate* is fine for pure functions with outputs the spec defines, tests, docs, and
    refactors that don't change behavior.
  - When unsure, recommend guiding.
- **Agree on behavior, not code.** Settle what should happen in each case: the condition,
  the status code and response, what does *not* change, and the audit entry. Check it
  against `docs/spec.md` and `openapi.yaml`. If they don't settle a case, it goes to the
  plan's open questions, not a guess. Then ask "Is this what we agreed?" before planning.
- **Plan only from what was agreed.** The plan makes no new decisions. If it has parts,
  name them and keep the same names from then on.

## While building

- **Stop at any fork the plan didn't settle.** Describe the options and what each means
  for whoever uses the API, recommend one, and ask. Never pick silently.
- **Never guess at causes.** When something fails, show the exact error and what you
  checked. Say "I don't know yet" rather than inventing an explanation.
- **Problems outside the task become follow-ups, not fixes.** Draft them and ask before
  creating anything. Don't quietly change code in another owner's area.
- **Nothing destructive or outward-facing without the person's explicit yes:**
  - running `acceptance/` against Launchpad, Orbit, or Team 21 (it resets the whole
    deployment)
  - deleting data, force pushes, rewriting history
  - secrets, tokens, or `.env` files
  - anything outside this repository
  - anything that posts to GitHub or another outside system: comments, issues, PRs, merges
- **Don't change settings to make your job easier.** No disabling CI checks, lint rules, or
  tests, and no skipping a failing test to get green. Tell the person what's in the way.

## Telling the person what happened

- **Lead with the answer.** Plain English, short, the conclusion first.
- **Questions are multiple choice,** with your recommendation first and a one-line reason.
  End every message that needs the person with exactly what you need.
- **Say what you tested and what you couldn't.** "Unit tests pass", "passes against local
  Postgres", and "passed against Orbit at SHA abc123" are different claims.
- **When you get something wrong, say so in a sentence,** fix it, and propose a change to
  this file if an instruction led to it.

## Humans stay in control

- **A human approves every code change.** Any PR that changes code, tests, migrations,
  workflows, or `openapi.yaml` needs approval from a teammate before it merges: the area
  owner, or another teammate if the owner wrote it. Agents never merge those PRs and never
  launch to Orbit.
- **Docs-only PRs** (plan, decision log, spec copy, guides) may be merged by the agent that
  wrote them once CI passes, if the person driving it allows that.
- **Fill in the PR template.** It asks what changed, how it differs from what was agreed,
  and what was tested for real. A reviewer should be able to judge the PR from it.
- **One plan task per PR,** small enough for a person to review properly.

## Handoffs

At the end of a session, update your owner's file in [`docs/handoff/`](docs/handoff/) and
only that file. It's how the next session, and the other teammates' agents, pick up
where you left off.

- **Rewrite it to the current state**, don't append. Sections: last updated (date and
  agent), where things stand, in progress (branches, half-done work), next up (plan task
  numbers), waiting on (who and what), notes for the next session.
- **Keep it short.** Task status belongs in `docs/plan.md`, settled questions in
  `docs/decisions.md`. Refer to them; don't copy them.
- **Files don't notify anyone.** If something is urgent, tell the person driving you to
  message the teammate directly.
- Commit the handoff update in the same PR as the work, or as its own docs-only PR.

## Branches and releases

- Branch from `main`, open a PR into `main`. There is no development branch.
- Merging to `main` deploys **Launchpad** (`team17-dev`) automatically. That is our
  development environment.
- **Orbit** (`team17-prod`, the one Team 21 and the instructors test) only changes when
  Quincy launches it from `main` by hand. That launch is the release step.
