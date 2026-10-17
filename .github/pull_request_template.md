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
- [ ] A human teammate will approve before merge (required for any code, test, migration, workflow, or `openapi.yaml` change)
