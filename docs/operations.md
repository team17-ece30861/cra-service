# Operations Guide

The short version of [platform.md](platform.md), for whoever is on call. Plan task 5.5.

## Deploy

Launchpad deploys automatically when a commit reaches `main` and CI passes. CI runs
Ruff, migration checks, Django checks, and tests against PostgreSQL.

Orbit is manual:

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

Rolling back traffic does not roll back the database. Reverse a migration only when it
is backward-compatible and the bad release has been reverted:

```bash
gcloud run jobs execute "$SERVICE-migrate" \
  --region "$REGION" \
  --wait \
  --args="manage.py,migrate,core,LAST_GOOD_MIGRATION,--noinput"
```

Reversing a migration does not restore deleted data.

For a lasting fix, revert the commit on `main`, let Launchpad redeploy, and then launch
Orbit. If Orbit traffic was pinned, unpin it only after the fixed revision is live.

## Rotate an API token

Tell the affected client before starting. The old token stops working once a new
instance reads the new Secret Manager version.

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

Redeploy the environment so its instances read the new value:

- Use **Launch to Orbit** for a `prod-*` secret.
- Re-run the latest successful CI deployment on `main` for `dev-api-token`.

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

Only after confirmation, disable the old version:

```bash
gcloud secrets versions disable OLD_VERSION --secret="$SECRET"
```

Never commit or share tokens.

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

A Cloud Run spend cap may stop Orbit. It does not reset itself.

Before lifting it:

1. Confirm the billing and Cloud Run spend-cap status.
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
