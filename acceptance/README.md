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

## Phase 5 HTTP gap checks

**Phase 5 HTTP gaps (5.10):** `http_gap_cases.py` adds 19 portable cases, shared
with `tests/test_http_gaps_api.py`; `test_http_gaps.py` is their HTTP entry point.
They cover AC-07 awareness/fix edits and audit/deadline recalculation, unchanged
state after rejected edits, PATCH/triage 404 and 413 precedence, and successful
`DELETE /test/clock`. The clock-release check compares returned UTC time and a
new ticket's receipt time with the runner's independent wall clock, allowing
120 seconds of skew on each side of the request window, and checks that the
released clock advances. Keep both machines' real clocks synchronized. It
restores the fixed test clock in `finally`; this is not a deployed-tester cleanup
implementation. With these cases the portable suite collects 241 tests.

These cases passed locally through Django and over an isolated loopback WSGI
server on 2026-11-20. They have not been run on Launchpad or Team 21. The separate
model-coverage inventory receives no new bindings from this increment.

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
also includes `operation_checks` when its test body executes or fixture setup
fails, and `teardown_complete`
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
- **`failed`:** the target answered and its status or schema check failed.
  **`inconclusive`:** no response arrived (connection failure or timeout), or the
  response checked successfully but its enclosing test failed or skipped, or
  teardown failed/interrupted without completion.
  Those are not passing evidence; passing observations require completed teardown.

Successful fixture setup/reset calls are excluded. On a setup failure, checked
operations are retained even when the `service` fixture fails before returning:
failed status/schema checks remain failed, and conforming setup responses are
inconclusive because their enclosing test failed. Setup alone supplies no passing
conformance or implementation evidence. Direct transport calls outside
`Service.expect` are also excluded;
add explicit checked cases to improve the table rather than guessing results.
Bodies not defined by the contract, such as the health response, are not validated.
Reports say `finished` only when the full collected selection reached terminal
outcomes and completed teardown without collection errors or deselection. Early
stops, interruption, filtered selections and collection errors say `incomplete`,
including an early exit that returns code 0. A fully attempted suite with failed
tests still says `finished` and retains its nonzero pytest exit code.

Selecting an individual file, node ID, subdirectory or multiple positional targets
is a partial selection, even when pytest emits no deselection event. A full-scope
run names the directory containing the selected pytest configuration, as the
documented command above does with `acceptance/pytest.ini` and `acceptance`.
Running with no path from a parent directory (for example `pytest -c
acceptance/pytest.ini` from the repository root) collects beyond the suite; the
report marks that `broader_selection` and says so in its reason.
Explicit `--ignore` and `--ignore-glob` exclusions also mark a run incomplete;
their paths are not copied into report metadata.

JSON adds `run_complete`, `tests_selected`, `tests_completed`, `tests_deselected`,
`tests_not_run`, `partial_selection`, `broader_selection`, `collection_exclusions`,
`collection_errors` and `incomplete_reasons`; existing result and
count fields are unchanged. Markdown and terminal summaries show the same counts
and reasons. `tests_not_run` counts selected IDs with no phase report; a test
interrupted after setup is started but not completed. Unobserved statuses remain
untested. The public portable copy must include `observations.py` with the changed
client and plugin.
Clock read/release map to REQ-16 from `docs/spec.md` because their contract
descriptions omit that requirement ID. Other IDs come from operation descriptions.

These exports belong to the standalone runner. They do not change the deployed
course `/tester/test/report` response or claim the new tester has been deployed.
Refresh `pod-k-shared/team17/tester/` through the normal approval/release process.

The integrated audit PUT/DELETE checks use raw transport because those methods
are not operations in the contract. They prove immutability in their tests, but
do not masquerade as GET audit 405 observations in this table. Its 405 status
therefore remains explicitly untested here. Statuses and list filters are covered by
`listing_cases.py` (PR #84).

## Phase 5 model-evaluation evidence

The approved [design mapping](../docs/model-coverage.md) and
`model_requirements.json` define 44 requirements and 266 fixed scenarios. Explicit
assertion checkpoints record evaluations, not pass-rate or implementation claims.
No test-name inference or historical CI results fill untested scenarios.

The deployed course tester includes `coverage.model` for explicitly configured
own-system targets and omits it for other teams. A published mapping URL must be
configured before claiming a usable measure; see the design mapping for settings
and release gates. The standalone JSON carries safe per-result `model_evidence`
plus version/availability metadata. Optional `--model-progress FILE` flushes that
evidence as each oracle completes, so an abort can retain it before teardown.

These counts differ from the operation table: a failed comparison evaluates a
design scenario but does not establish passing conformance. CI-only checks,
skipped work, missing bindings and manual demos do not become suite evidence.

## Malformed requests (AC-13)

`malformed.py` sends at least 500 malformed requests that Schemathesis generates from
`openapi.yaml` (contract 0.3.0). Requests are deduplicated so each one sent has a
different invalid input; different invalid values for the same field count separately
(an unknown report type `+` and `Ø` are two requests). The run reports three numbers:
requests sent, distinct invalid inputs (always equal), and fault categories, keyed by
operation, location and field (array indices collapsed), and rule. The JSON summary lists
the categories per operation.
The seed is fixed, so every run on one operating system sends the same corpus. Linux and
macOS generate different corpora even with the same Python patch release (3.12.16) and
identical installed package versions (checked on 2026-11-22 in a `python:3.12-slim`
container against CI's install log): Linux sends 664 requests (`34824b069854e3e9`), macOS
sends 683 (`562ec91fbc181557`). Both cover the same 133 fault categories; only the invalid
values differ. The corpus is generated wherever the CLI or CI runs (the production image
doesn't include Schemathesis). Both sizes and fingerprints are recorded in `malformed.py`.
CI checks only the Linux one; the macOS one is checked only when the test or the CLI runs
on a Mac, so it can go stale unnoticed. Each request must
get the status the contract's precedence gives (404 for an unknown report type, 413 over
64 KB, otherwise 400) as problem+json matching the contract, never a 5xx, and the stored
data must be unchanged afterwards. CI runs the Linux corpus in-process
(`tests/test_malformed_requests.py`). Unlike the suite above it needs Python 3.12 and the
dev requirements (`pip install -r requirements-dev.txt`); other versions generate a
different corpus, so the CLI refuses them and warns if the fingerprint differs.

```bash
export CRA_BASE_URL=https://<deployment-base-url>
export CRA_API_TOKEN=<token>        # never printed
python -m acceptance.malformed --out malformed.json            # target must be empty
python -m acceptance.malformed --reset --out malformed.json    # wipes the whole deployment first and after
```

Without `--reset` it refuses to run against a target that holds tickets, and it leaves its
two seed tickets behind. With `--reset` it resets before and after the run and releases the
clock. It exits 0 only if every response matched and nothing was stored.

## Results

The suite collects 241 cases (59 Phase 3/audit, 32 drafts, 63 submissions, 34 closure, 22
statuses and listing, 11 no-change updates, 1 confidentiality sweep, 19 Phase 5 HTTP gaps). On
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
| `model_coverage.py` | Explicit design evaluations, abort journal and own-model aggregation |
| `model_requirements.json` | Versioned 44-requirement / 266-scenario design and exact bindings |
| `conftest.py` | Safety options, completed-test observations and JSON/table exports |
| `test_phase3.py` | HTTP entry point, including the plain-HTTP (AC-15) probe |
| `draft_cases.py` | Live-draft cases shared by local Django and HTTP runs |
| `test_drafts.py` | HTTP entry point for draft-read checks |
| `submission_cases.py` | Actual recording cases shared by Django and HTTP |
| `test_submissions.py` | HTTP recording entry point |
| `closure_cases.py` | Portable closure and append-only lifecycle cases |
| `test_closures.py` | HTTP closure/lifecycle entry point |
| `listing_cases.py` | AC-06 statuses through E6 and AC-11 list filters and order |
| `test_listing.py` | HTTP entry point for statuses and listing |
| `update_cases.py` | Q6: a PATCH that changes nothing adds no audit entry |
| `test_updates.py` | HTTP entry point for the Q6 cases |
| `http_gap_cases.py` | Phase 5 AC-07, PATCH/triage 404/413 and successful clock release |
| `test_http_gaps.py` | HTTP entry point for the Phase 5 gap cases |
| `privacy_cases.py` | AC-16: the reporter appears only in `GET /tickets/{id}` |
| `test_privacy.py` | HTTP entry point for the confidentiality sweep |
