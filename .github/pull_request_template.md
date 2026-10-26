## What this does

<!-- Two or three sentences, plain English. -->

Plan task: <!-- e.g. 4.D1, or "none" -->

## Differences from what was agreed

<!-- Anything that differs from docs/spec.md, openapi.yaml, or what you agreed with the
person who assigned it. Write "None" if there are none. -->

## How it was tested

- [ ] Unit tests
- [ ] Full suite against local Postgres (`pytest -q`)
- [ ] Against a deployment (which one, and which commit):

Not tested for real (mocked, skipped, or not run):

## Risks and follow-ups

<!-- Anything a reviewer should look at closely, open questions, and work left for later. -->

## Checklist

- [ ] `ruff check . && ruff format --check .` pass
- [ ] `python manage.py makemigrations --check --dry-run` passes
- [ ] Plan status updated in `docs/plan.md` (if this finishes a task)
- [ ] Entry added to `docs/decisions.md` (if this settles a question or changes scope, the contract, or ownership)
- [ ] Changes what Orbit does? `pod-k-shared` update PR drafted (status chart and `team17/TESTING.md`), to merge after the next Orbit launch. Otherwise: not needed
- [ ] Independent review before merge: a teammate, or an agent that didn't write this PR, posts an approving review (required for code, tests, and migrations). Workflow and `openapi.yaml` changes need a human teammate's approval
