# Team 17 CRA Reporting Service

Django 5.2 + Django Ninja on Cloud Run, Postgres on Neon.
The contract is `openapi.yaml`. Match it exactly; Ninja's /docs page is not the source of truth.

## Commands
- Local DB: `docker compose up -d`, then `set -a; source .env; set +a`
- Tests: `pytest -q`
- Lint: `ruff check . && ruff format --check .`
- Migrations check: `python manage.py makemigrations --check --dry-run`

## Rules
- Never call datetime.now() or timezone.now() directly. Use the clock helper in core/clock.py.
- All times are UTC. Return timestamps as UTC to the second; truncate fractional seconds.
- Errors use application/problem+json. 400 = schema, 422 = business rule, per openapi.yaml.
- Error precedence when several apply: 401, 413, 404, 400, 409, 422.
- /health stays public. Every other endpoint requires `Authorization: Bearer <API_TOKEN>`.
- Requests that change ticket data require the X-Actor header (missing or empty = 400).
  The /test/* endpoints do not require it.
- Unknown fields and system-set fields in request bodies return 400.
- Reporter details appear only in GET /tickets/{id}, never anywhere else.
- A failed request changes nothing.
- Never log request bodies.
- Don't edit .github/workflows/deploy.yml or orbit.yml unless the task says to.
- Work on a branch and open a PR. Never push to main.
