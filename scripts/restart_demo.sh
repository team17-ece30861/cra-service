#!/usr/bin/env bash
# AC-19 (REQ-18) restart demonstration, meant to be screen-recorded.
#
# 1. Creates a ticket, triages it as actively exploited, and records its early warning.
# 2. Saves the ticket, the early-warning report, and the audit log.
# 3. Forces a new Cloud Run revision (a harmless env var change), which replaces every
#    running instance, and waits until the new revision serves traffic.
# 4. Reads the same three things again and shows they are byte-for-byte unchanged.
#
# Usage:  scripts/restart_demo.sh dev|prod
#   dev  = Launchpad (team17-dev),  token secret dev-api-token
#   prod = Orbit     (team17-prod), token secret prod-api-token-team17
#
# The token is read from Secret Manager into a variable and never printed. The script
# does not reset the deployment; it adds one ticket named "AC-19 restart demo".
set -euo pipefail

ENV="${1:-}"
case "$ENV" in
  dev)  SERVICE=team17-dev;  SECRET=dev-api-token ;;
  prod) SERVICE=team17-prod; SECRET=prod-api-token-team17 ;;
  *) echo "usage: $0 dev|prod" >&2; exit 2 ;;
esac
REGION=us-central1
PROJECT="${GOOGLE_CLOUD_PROJECT:-team17-ece30861}"

BASE=$(gcloud run services describe "$SERVICE" --region "$REGION" --project "$PROJECT" --format='value(status.url)')
TOKEN=$(gcloud secrets versions access latest --secret="$SECRET" --project "$PROJECT")
OUT=$(mktemp -d)
step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
api() {  # api METHOD PATH [JSON]
  local args=(-sS -X "$1" "$BASE$2" -H "Authorization: Bearer $TOKEN" -H "X-Actor: ac19-demo")
  [[ $# -ge 3 ]] && args+=(-H "Content-Type: application/json" --data "$3")
  curl "${args[@]}" -w '\n'
}
field() { python3 -c "import sys,json; print(json.load(sys.stdin)$1)"; }

step "Service: $SERVICE at $BASE"
REV_BEFORE=$(gcloud run services describe "$SERVICE" --region "$REGION" --project "$PROJECT" --format='value(status.latestReadyRevisionName)')
echo "Serving revision: $REV_BEFORE"
api GET /health

NOW=$(api GET /test/clock | field "['now']")
echo "Service clock: $NOW"
AWARE=$(python3 -c "import datetime as d; t=d.datetime.fromisoformat('$NOW'.replace('Z','+00:00')); print((t-d.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ'))")

step "1. Create a ticket"
TICKET=$(api POST /tickets '{
  "source": "external_researcher",
  "title": "AC-19 restart demo",
  "description": "Ticket used to show that data survives a restart.",
  "product": {"manufacturer": "Acme", "name": "Router OS", "affected_versions": ["4.1.0"]},
  "member_states": ["DE"],
  "vulnerability": {"description": "Authentication can be bypassed."},
  "exploit": {"description": "Observed exploitation."},
  "sensitivity": "AMBER"
}')
ID=$(printf '%s' "$TICKET" | field "['id']")
echo "Created ticket $ID"

step "2. Triage it as actively exploited (aware 1 hour ago)"
api POST "/tickets/$ID/triage" "{\"decision\": \"actively_exploited\", \"aware_at\": \"$AWARE\", \"reason\": \"Exploitation observed.\"}" | field "['state']"

step "3. Record the early warning as submitted now"
api POST "/tickets/$ID/reports/early_warning/submission" "{\"submitted_at\": \"$NOW\"}" | field "['status']"

step "4. Read the ticket, the early warning, and the audit log BEFORE the restart"
api GET "/tickets/$ID" > "$OUT/ticket.before.json"
api GET "/tickets/$ID/reports/early_warning" > "$OUT/report.before.json"
api GET "/tickets/$ID/audit" > "$OUT/audit.before.json"
python3 -m json.tool "$OUT/report.before.json" | head -20
python3 - "$OUT/audit.before.json" <<'PY'
import json, sys
body = json.load(open(sys.argv[1]))
entries = body if isinstance(body, list) else body.get("entries", body.get("items", []))
print(f"Audit entries: {len(entries)}")
for e in entries:
    print(f"  {e.get('at')}  {e.get('action')}  by {e.get('actor')}")
PY

step "5. Restart: deploy a new revision (harmless env var change) and wait for it"
gcloud run services update "$SERVICE" --region "$REGION" --project "$PROJECT" \
  --update-env-vars "AC19_RESTART_MARKER=$(date -u +%Y%m%dT%H%M%SZ)" --quiet
REV_AFTER=$(gcloud run services describe "$SERVICE" --region "$REGION" --project "$PROJECT" --format='value(status.latestReadyRevisionName)')
echo "Revision before: $REV_BEFORE"
echo "Revision after:  $REV_AFTER"
[[ "$REV_BEFORE" != "$REV_AFTER" ]] || { echo "No new revision was created" >&2; exit 1; }
api GET /health

step "6. Read the same three things AFTER the restart"
api GET "/tickets/$ID" > "$OUT/ticket.after.json"
api GET "/tickets/$ID/reports/early_warning" > "$OUT/report.after.json"
api GET "/tickets/$ID/audit" > "$OUT/audit.after.json"

step "7. Compare"
status=0
for f in ticket report audit; do
  if cmp -s "$OUT/$f.before.json" "$OUT/$f.after.json"; then
    echo "  $f: unchanged"
  else
    echo "  $f: CHANGED"; diff "$OUT/$f.before.json" "$OUT/$f.after.json" || true; status=1
  fi
done
[[ $status -eq 0 ]] && echo "PASS: ticket, report, and audit log survived the restart (AC-19)." \
                    || echo "FAIL: something changed across the restart."
echo "Saved responses: $OUT"
exit $status
