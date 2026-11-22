# Operations Guide

The short version of [platform.md](platform.md), for whoever is on call. Plan task 5.5.

## Deploy

Launchpad deploys automatically when a commit reaches `main` and CI passes. CI runs
Ruff, migration checks, Django checks, and tests against PostgreSQL.

Only Quincy launches Orbit, including releases for recovery or token rotation. Agents
never launch it. Quincy's manual procedure is:

1. Open **Actions → Launch to Orbit**.
2. Run it on `main`.
3. Enter `ORBIT`.

Do not run Orbit launches from another branch. The service URL comes from the
`PROD_HOST` repository variable; never publish an internal Cloud Run URL.

Before deployment, confirm the migration is backward compatible: the old revision may
run against the new schema for a short period.

## Migrations

Migrations run in `team17-ENV-migrate` before the new revision is deployed. They never
run at container startup.

A migration must work with both the current and previous release:

- Add tables or nullable columns first.
- Roll out code before dropping or renaming columns.
- Keep migrations reversible where possible.

If a migrate job fails, the deployment stops and the existing revision remains live.

To inspect a migration run:

```bash
gcloud run jobs executions list \
  --job team17-ENV-migrate \
  --region us-central1
```

## Roll back

Cloud Run keeps previous revisions. Roll back by sending 100% of traffic to the last
known-good revision:

```bash
SERVICE=team17-prod
REGION=us-central1

gcloud run revisions list \
  --service "$SERVICE" \
  --region "$REGION"

gcloud run services update-traffic "$SERVICE" \
  --region "$REGION" \
  --to-revisions REVISION_NAME=100
```

Check the service, then pin or unpin traffic deliberately (`HOST` is the `PROD_HOST`
or `DEV_HOST` repository variable):

```bash
curl -fsS "https://$HOST/health"

gcloud run services update-traffic "$SERVICE" \
  --region "$REGION" \
  --to-latest
```

Do not unpin to the latest revision until the fix is deployed.

Rolling back traffic does not roll back the database. Before reversing a migration,
Quincy must confirm that the resulting schema works with every revision still serving
and that the reverse operations will not lose required data. Choose the affected app
(`core`, `console` or `tester`) and its last good migration; do not assume `core`.

Inspect the migrate job's container image in Cloud Run. It must contain the migration
files being reversed, their dependencies and the selected target. A later deployment
may have changed that image; stop if it is missing those files. First inspect the
rollback plan using that job and the correct environment database:

```bash
APP=APP_LABEL
TARGET=LAST_GOOD_MIGRATION

gcloud run jobs execute "$SERVICE-migrate" \
  --region "$REGION" \
  --wait \
  --args="manage.py,migrate,$APP,$TARGET,--plan"
```

Replace both placeholders before running. Read the execution logs and inspect the full
plan, including dependent apps. After Quincy approves that plan, run the same target:

```bash
gcloud run jobs execute "$SERVICE-migrate" \
  --region "$REGION" \
  --wait \
  --args="manage.py,migrate,$APP,$TARGET,--noinput"
```

Reversing a migration does not restore deleted data.

For a lasting fix, revert or fix the commit on `main`, let Launchpad redeploy, and have
Quincy launch Orbit. If traffic was pinned, inspect the new ready revision and its
image before moving traffic; the deployment's `/health` smoke test still hits the old
pinned revision. Do not unpin to an unfixed release.

## Rotate an API token

Tell the affected client before starting and coordinate a window without an active
deployed-tester run. Tokens are environment variables resolved at instance startup:
existing instances retain their cached value, while a cold start can read the new
`latest` version before redeployment. Plan the client handoff for this transition.

```bash
SECRET=prod-api-token-team21
```

Create a new secret version:

```bash
printf '%s' "$(openssl rand -hex 32)" |
  gcloud secrets versions add "$SECRET" --data-file=-
```

Record the old version number:

```bash
gcloud secrets versions list "$SECRET"
```

Check Cloud Run's traffic allocation before redeploying. A redeployment refreshes the
new revision's instances, not instances still serving a pinned revision:

- Quincy uses **Launch to Orbit** for a `prod-*` secret; agents never launch it.
- Re-run the latest successful CI deployment on `main` for `dev-api-token`.

If traffic is pinned after a rollback, first fix or revert the bad code on `main` and
validate that code on Launchpad. For Orbit, Quincy then launches the fixed `main` there.
In either environment, inspect the new ready revision's image/commit and secret mapping;
`/health` on the service URL still checks the pinned revision. Only then direct traffic
to that verified revision,
using its name with the rollback section's `--to-revisions` command. Do not use
`--to-latest` merely to rotate a token: the latest revision may still contain the bug.
If no safe replacement is ready, coordinate recovery with Quincy; do not treat a
successful redeploy as completed rotation while traffic remains pinned.

Wait for the traffic change to finish before checking the serving token. Existing
instances can keep the old token during the transition. See Google's
[secret startup behavior](https://docs.cloud.google.com/run/docs/configuring/services/secrets)
and [traffic allocation rules](https://docs.cloud.google.com/run/docs/rollouts-rollbacks-traffic-migration).

Send the new token to the client privately:

```bash
gcloud secrets versions access latest --secret="$SECRET"
```

Confirm the new token works, without printing it:

```bash
NEW_TOKEN=$(gcloud secrets versions access latest --secret="$SECRET")
curl -fsS \
  -H "Authorization: Bearer $NEW_TOKEN" \
  "https://$HOST/test/clock"
```

Confirm requests with the old token now receive 401 on the same endpoint, without
printing either token. Only after traffic is on the verified replacement and these
checks pass, disable the old version:

```bash
gcloud secrets versions disable OLD_VERSION --secret="$SECRET"
```

Disabling a Secret Manager version does not revoke a token already cached by a running
instance. Never commit tokens or share them outside the intended private handoff.

## Read logs

Cloud Run request and application logs are available in Google Cloud Logging. The
Gunicorn access log uses the combined format, with the client whose token matched in the
user field (`-` when no token matched):

```text
169.254.1.1 - team21 [05/Oct/2026:19:27:49 +0000] "GET /test/clock HTTP/1.1" 200 31 "-" "python-requests/2.32.3"
```

The access log also includes the request method, path, status, and response size (the
compressed size when the client asked for gzip).

Do not search for or print tokens or request bodies. They must not appear in logs.

Useful checks:

- `5xx` responses indicate a server failure.
- `401` responses indicate a missing or invalid bearer token.
- Migration failures appear in `team17-ENV-migrate` execution logs.
- Deploy and smoke-test failures appear in the corresponding GitHub Actions run.

Any 5xx on `team17-prod` or `team17-dev` emails the platform owner (Cloud Monitoring
policies "Team 17: server errors on SERVICE", created by `scripts/create_5xx_alert.sh`).
The email links the incident; read the stack trace in Cloud Logging with
`severity>=ERROR` for that service. The incident closes by itself after 30 minutes
without server errors.

A `200` from `GET /health` means Django loaded. It does not check the Neon database or
migration state.

## Lift the spend cap

The repository records a $10 Cloud Run cap but does not capture its live configuration.
Quincy must confirm the budget type, scope, amount, period and enforcement status in
Cloud Billing before recovery. An alerts-only budget does not cap usage.

Google's built-in spend-cap budgets automatically reset at the next budget period;
manual lifting resumes usage earlier and removes enforcement for the rest of that
period unless the budget amount is increased. Custom shutdown automation may need
different recovery. See the
[spend-cap documentation](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps).

Before lifting it:

1. Confirm the configured mechanism and whether it actually blocked Cloud Run.
2. Check recent Cloud Run and Neon usage.
3. Confirm the cap was not triggered by an unintended load or test run.
4. Lift the cap with Quincy or the person responsible for hosting.

After lifting it, verify:

```bash
curl -fsS "https://$PROD_HOST/health"
```

Then communicate separately whether Orbit is serving and whether data is unchanged.

Do not change the spend limit, billing configuration, or Cloud Run instance settings
without the platform owner's approval.

## Test-environment safety

Use Launchpad for Team 17 test work unless a cross-team window has been explicitly
booked. Never point the acceptance suite at Orbit or Team 21 without approval.

`POST /test/reset` deletes all tickets, reports, and audit entries. It does not release
a fixed clock. Call `DELETE /test/clock` for real time.

Run test suites one at a time against a deployment. The deployed tester refuses a second
run while one is going (409), and a run holds one Gunicorn worker for up to 30 minutes.

## Console sign-in lockout

Five failed console sign-ins for one username within 15 minutes lock that username for
15 minutes from the fifth failure. The lock ends by itself, and `POST /test/reset` does
not clear it. To clear it early, run this with that environment's `DATABASE_URL`:

```bash
python manage.py shell -c "from console.lockout import username_key; \
from console.models import SignInFailure; \
SignInFailure.objects.filter(username=username_key('USERNAME')).delete()"
```

Console accounts are created with `python manage.py createsuperuser` against the same
database (see `docs/platform.md`, "Console accounts").
