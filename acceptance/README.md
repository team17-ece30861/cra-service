# Acceptance test runner

Black-box tests for the pod's common interface (`openapi.yaml`). They run over HTTP(S)
against any deployment, needing only its base URL and an access token, and know nothing
about how the service is built. The same cases also run inside our CI through Django's
test client (`tests/test_phase3_api.py`).

**Covers (Phase 3):** AC-01 to AC-05, AC-14, AC-15, and AC-17, plus the Model D E6
boundary. Every response is also checked against the response schemas in `openapi.yaml`.

**Draft-read increment (4.A2):** `draft_cases.py` adds 32 portable live-draft
cases shared with `tests/test_draft_api.py`; `test_drafts.py` is the HTTP entry
point. The suite now collects 87 cases. Local stored-row fixtures cover locked
reads but do not establish submission POST behavior. Q3/Q4 use documented plan
proposals. No Phase 4 deployment run is claimed.

**Submission increment (4.A3):** `submission_cases.py` adds 63 portable actual-POST
cases, shared with `tests/test_submission_api.py`. Coverage includes snapshots,
one audit, failures, schema/time/order/duplicates, auth/size precedence and reset.
Local persistence/fault tests supplement them; a genuine race requires PostgreSQL.
This is not closure or Ann's full Ticket/list status integration.

**Closure increment (4.A4):** `closure_cases.py` adds 34 portable closure/lifecycle
cases shared with `tests/test_closure_api.py`; `test_closures.py` is the HTTP entry.
Closed reads, rejection of changes, locked snapshots, auth/size/actor precedence,
one audit and AC-12 audit sequencing/405s are checked. Local storage/fault/race
tests supplement these. The combined local HTTP run had one Windows connection
abort; it is not a passing deployed result. Ann's 4.A5 remains separate.

**Audit failure increment (4.T6):** four additional shared `Phase3Checks` cases
cover unknown UUID/malformed-ID 404 and audit PUT/DELETE 405. They check problem
schemas and unchanged ticket/list/audit data, without requiring example title
wording. These complement the complete lifecycle cases; service behavior is unchanged.

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

## Operation-status evidence (4.T5)

The runner lists every contract operation, its method/path and referenced
requirements, implementation evidence, and success/error response checks. For an
authorized run, add output paths to the command above:

```bash
python -m pytest -c acceptance/pytest.ini acceptance --allow-reset -v \
  --tested-version <deployed-commit> --report results.json \
  --operation-report operations.md
```

The version is a supplied label, not independently verified deployment identity.
The JSON report retains its existing fields and adds `operations`; each result
also includes `operation_checks` when its test body executes and `teardown_complete`
to distinguish finished tests from interrupted teardown. New evidence stores
only contract method/path templates, expected/actual status codes, and whether
the status and defined response schema checked successfully. It stores no token,
actor, resource identifier, request body, or response body.

- **Implementation `success_observed`:** an expected 2xx checked successfully in
  a passing test. This is not a declaration that every requirement is implemented.
  A working unfiltered list, for example, does not prove its filters work.
- **`not_demonstrated`:** no passing successful-response check. Correct 401s on
  an otherwise unbuilt route do not demonstrate implementation.
- **Conformance `passed`:** every explicitly declared status in that category
  has a passing check, and no observed check failed or is inconclusive. This is
  status-code coverage, not exhaustive behavioral or code coverage.
- **`partial`:** some declared statuses passed; others remain untested.
  **`not_tested`:** no observations for the category. **`not_defined`:** the
  contract declares no statuses in that category, as with health-check errors.
- **`failed`:** a reached status/schema check failed (including communication
  failure). **`inconclusive`:** the response checked successfully but its enclosing
  test failed or skipped, or teardown failed/interrupted without completion.
  Those are not passing evidence; passing observations require completed teardown.

Per-test fixture setup/reset calls are excluded, so setup alone cannot prove an
operation. Direct transport calls outside `Service.expect` are also excluded;
add explicit checked cases to improve the table rather than guessing results.
Bodies not defined by the contract, such as the health response, are not validated.
Interrupted runs say `incomplete`; all unobserved statuses remain untested.
Clock read/release map to REQ-16 from `docs/spec.md` because their contract
descriptions omit that requirement ID. Other IDs come from operation descriptions.

These exports belong to the standalone runner. They do not change the deployed
course `/tester/test/report` response or claim the new tester has been deployed.
Refresh `pod-k-shared/team17/tester/` through the normal approval/release process.

The integrated audit PUT/DELETE checks use raw transport because those methods
are not operations in the contract. They prove immutability in their tests, but
do not masquerade as GET audit 405 observations in this table. Its 405 status
therefore remains explicitly untested here. A passing list response likewise
does not establish Ann's pending filtering/status work.

## Results

This increment collects 188 cases (59 Phase 3/audit, 32 drafts, 63 submissions, 34 closure). On
localhost the plain-HTTP probe is skipped. These are collection/expected counts,
not a new deployed result; earlier Phase 3 validation covered only the original 55.

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
| `client.py` | HTTP transport, response checks and safe observation metadata |
| `reporting.py` | Pure operation evidence aggregation and Markdown rendering |
| `conftest.py` | Safety options, completed-test observations and JSON/table exports |
| `test_phase3.py` | HTTP entry point, including the plain-HTTP (AC-15) probe |
| `draft_cases.py` | Live-draft cases shared by local Django and HTTP runs |
| `test_drafts.py` | HTTP entry point for draft-read checks |
| `submission_cases.py` | Actual recording cases shared by Django and HTTP |
| `test_submissions.py` | HTTP recording entry point |
| `closure_cases.py` | Portable closure and append-only lifecycle cases |
| `test_closures.py` | HTTP closure/lifecycle entry point |
