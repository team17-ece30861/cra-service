# Team 17 CRA Reporting Service

Django + Django Ninja service for the ECE 30861 pod project. The pod's shared
`openapi.yaml` is the API contract; the auto-generated `/docs` page is only a convenience.

## Deployments

| Nickname | Cloud Run service | URL | Purpose |
|---|---|---|---|
| Launchpad | `team17-dev` | https://team17-dev-7zneiwx4ba-uc.a.run.app | Development. Deploys automatically on every merge to `main`. |
| Orbit | `team17-prod` | https://team17-prod-7zneiwx4ba-uc.a.run.app | The evaluation deployment used by Team 21 and the instructors. Deploys only by manual launch. |

Both run in `us-central1` with min instances 0 and max instances 1. Each uses its own
Neon Postgres project and its own secrets. The first request after a period of idle
takes a few seconds while an instance starts.

Use only these URLs. Each service accepts just its own hostname (the `DEV_HOST` and
`PROD_HOST` repository variables), so the other URL Cloud Run shows for it
(`…-720849560682.us-central1.run.app`) returns 400. Every endpoint except `GET /health`
needs the API token, which is in Secret Manager:
`gcloud secrets versions access latest --secret=prod-api-token` (or `dev-api-token`).

## Local development

Requires Python 3.12 and Docker.

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
docker compose up -d                 # local Postgres 18
cp .env.example .env
set -a; source .env; set +a
python manage.py migrate
python manage.py runserver           # http://localhost:8000/health
```

## Tests and lint

```bash
pytest -q
ruff check . && ruff format --check .
```

CI runs these on every push and pull request against a Postgres 18 service container.

## Deploying

- **Launchpad:** merge to `main`. CI tests, builds the image, runs migrations as a Cloud
  Run job, deploys `team17-dev`, and smoke-tests `/health`.
- **Orbit:** Actions tab → **Launch to Orbit** → Run workflow on `main` → type `ORBIT`.
  The same test, migrate, deploy, and smoke-test steps run against `team17-prod`.

Migrations never run at container startup.

## Configuration

All settings come from environment variables. On Cloud Run, secrets are injected from
Secret Manager:

| Variable | Source |
|---|---|
| `DATABASE_URL` | `<env>-database-url` (Neon pooled connection string) |
| `DJANGO_SECRET_KEY` | `<env>-django-secret-key` |
| `API_TOKEN` | `<env>-api-token` |
| `DJANGO_DEBUG`, `ALLOWED_HOSTS` | Set by the deploy workflow (`ALLOWED_HOSTS` from `DEV_HOST` or `PROD_HOST`) |

GitHub repository variables used by the workflows (not secrets):
`GCP_PROJECT_ID`, `GCP_REGION`, `GCP_WIF_PROVIDER`, `GCP_DEPLOY_SA`, `DEV_HOST`, `PROD_HOST`.

Architecture, rollback, cost controls, and known limitations are in
[docs/platform.md](docs/platform.md).

## Team conventions

- Get the current time only through `core.clock.now()`, never `datetime.now()` or
  `timezone.now()` directly. It honours the fixed test clock (`PUT /test/clock`).
- Store all times in UTC.
- Never log request bodies.
- Deadline and state logic stay as pure Python, separate from views and models.
