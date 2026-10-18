# Acceptance test runner

Black-box tests for the pod's common interface (`openapi.yaml`). They run over HTTP(S)
against any deployment, needing only its base URL and an access token, and know nothing
about how the service is built. The same cases also run inside our CI through Django's
test client (`tests/test_phase3_api.py`).

**Covers (Phase 3):** AC-01 to AC-05, AC-14, AC-15, and AC-17, plus the Model D E6
boundary. Every response is also checked against the response schemas in `openapi.yaml`.

## Warning: it resets the target

Every test starts with `POST /test/reset`, which deletes **all** tickets on the target
deployment, for every client. Run it only against a deployment you're allowed to reset, at
an agreed time, and never two runs at once. It refuses to start without `--allow-reset`.

## Run it

Needs Python 3.12 or later and a checkout of this repository (it reads `openapi.yaml` and
`tests/fixtures/`). Django and a database are **not** needed.

```bash
python3 -m venv .venv-acceptance
source .venv-acceptance/bin/activate
pip install pytest PyYAML "jsonschema[format-nongpl]"

export CRA_BASE_URL=https://<deployment-base-url>
export CRA_API_TOKEN=<token>        # sent to you privately; never commit it or paste it into a prompt
python -m pytest -c acceptance/pytest.ini acceptance --allow-reset -v
```

Run it from the repository root.

| Option | Meaning |
|---|---|
| `--base-url URL` | Target deployment. Defaults to `CRA_BASE_URL`. Must be HTTPS, except for `localhost`. |
| `--allow-reset` | Required. Confirms you may reset the target. |
| `--tested-version LABEL` | Optional label recorded in the report (for example, a commit). Defaults to `CRA_TESTED_VERSION`. |
| `--report FILE` | Optional JSON report: run times, target, counts, and each test's outcome. It never contains the token or request bodies. |

## Results

On an HTTPS deployment all 55 tests should pass. Against `http://localhost`, the plain-HTTP
check (AC-15) is skipped, so expect 54 passed and 1 skipped.

The first request after the service has been idle can take several seconds while it starts,
and the client allows 30 seconds per request.

Afterward, the target holds the last test's data and a fixed test clock. To leave it clean:

```bash
curl -X POST   "$CRA_BASE_URL/test/reset" -H "Authorization: Bearer $CRA_API_TOKEN"
curl -X DELETE "$CRA_BASE_URL/test/clock" -H "Authorization: Bearer $CRA_API_TOKEN"
```

## Files

| File | Purpose |
|---|---|
| `cases.py` | The test cases, shared by the HTTP and in-process runs |
| `client.py` | HTTP transport, plus response checks against `openapi.yaml` |
| `conftest.py` | Command-line options, safety checks, and the JSON report |
| `test_phase3.py` | HTTP entry point, including the plain-HTTP (AC-15) probe |
