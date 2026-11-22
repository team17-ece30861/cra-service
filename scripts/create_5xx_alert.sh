#!/usr/bin/env bash
# Creates (or updates) the Cloud Monitoring alert that emails when a deployment returns
# server errors. Plan task 5.8 (4.P4).
#
# Usage:  scripts/create_5xx_alert.sh EMAIL [SERVICE ...]
#   EMAIL    where alerts go (an email notification channel is created once and reused)
#   SERVICE  Cloud Run services to watch (default: team17-prod team17-dev)
#
# Condition: any 5xx response (Cloud Run's built-in run.googleapis.com/request_count with
# response_code_class="5xx") in a 5-minute window, per service. The incident closes on its
# own after 30 minutes without server errors. Uses the Monitoring REST API with your
# gcloud credentials, so no gcloud alpha/beta components are needed. Re-running replaces
# the policy with the same display name instead of adding a second one.
set -euo pipefail

EMAIL="${1:?usage: $0 EMAIL [SERVICE ...]}"
shift
SERVICES=("$@")
[[ ${#SERVICES[@]} -gt 0 ]] || SERVICES=(team17-prod team17-dev)
PROJECT="${GOOGLE_CLOUD_PROJECT:-team17-ece30861}"
API="https://monitoring.googleapis.com/v3/projects/$PROJECT"
TOKEN=$(gcloud auth print-access-token)
call() { curl -sS -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" "$@"; }

# 1. Email channel (reuse one with the same address).
CHANNEL=$(call "$API/notificationChannels" | python3 -c "
import json, sys
d = json.load(sys.stdin)
for c in d.get('notificationChannels', []):
    if c.get('type') == 'email' and c.get('labels', {}).get('email_address') == sys.argv[1]:
        print(c['name']); break
" "$EMAIL")
if [[ -z "$CHANNEL" ]]; then
  BODY=$(python3 -c 'import json, sys; print(json.dumps({"type": "email", "displayName": "Team 17 alerts", "labels": {"email_address": sys.argv[1]}}))' "$EMAIL")
  RESPONSE=$(call -X POST "$API/notificationChannels" --data "$BODY")
  CHANNEL=$(printf '%s' "$RESPONSE" | python3 -c 'import json, sys; print(json.load(sys.stdin).get("name", ""))' 2>/dev/null || true)
  [[ -n "$CHANNEL" ]] || { echo "Could not create the channel: $RESPONSE" >&2; exit 1; }
  echo "Created notification channel $CHANNEL"
else
  echo "Reusing notification channel $CHANNEL"
fi

# 2. One policy per service.
for SERVICE in "${SERVICES[@]}"; do
  NAME="Team 17: server errors on $SERVICE"
  POLICY=$(python3 - "$SERVICE" "$NAME" "$CHANNEL" <<'PY'
import json, sys
service, name, channel = sys.argv[1:]
print(json.dumps({
    "displayName": name,
    "combiner": "OR",
    "conditions": [{
        "displayName": f"5xx responses from {service}",
        "conditionThreshold": {
            "filter": (
                'resource.type = "cloud_run_revision" '
                f'AND resource.labels.service_name = "{service}" '
                'AND metric.type = "run.googleapis.com/request_count" '
                'AND metric.labels.response_code_class = "5xx"'
            ),
            "aggregations": [{
                "alignmentPeriod": "300s",
                "perSeriesAligner": "ALIGN_SUM",
                "crossSeriesReducer": "REDUCE_SUM",
                "groupByFields": ["resource.labels.service_name"],
            }],
            "comparison": "COMPARISON_GT",
            "thresholdValue": 0,
            "duration": "0s",
            "trigger": {"count": 1},
        },
    }],
    "alertStrategy": {"autoClose": "1800s"},
    "notificationChannels": [channel],
    "documentation": {
        "mimeType": "text/markdown",
        "content": (
            f"{service} returned a server error. Read the error with stack trace in "
            "Cloud Logging (severity>=ERROR for this service); docs/platform.md, "
            "'Reading logs', explains the log lines. Request bodies are never logged."
        ),
    },
}))
PY
)
  EXISTING=$(call "$API/alertPolicies" | python3 -c "
import json, sys
for p in json.load(sys.stdin).get('alertPolicies', []):
    if p.get('displayName') == sys.argv[1]:
        print(p['name']); break
" "$NAME")
  if [[ -n "$EXISTING" ]]; then
    call -X PATCH "https://monitoring.googleapis.com/v3/$EXISTING" --data "$POLICY" >/dev/null
    echo "Updated $EXISTING ($NAME)"
  else
    RESULT=$(call -X POST "$API/alertPolicies" --data "$POLICY")
    echo "$RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); print('Created', d['name'], '(' + d['displayName'] + ')') if 'name' in d else sys.exit(json.dumps(d))"
  fi
done
