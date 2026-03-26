#!/bin/bash
# Fires a test PagerDuty-format webhook at localhost
# Usage: ./scripts/test_alert.sh [p1|p2|p3]
# Requires: curl, optionally PAGERDUTY_WEBHOOK_SECRET in .env for HMAC

set -euo pipefail

SEVERITY=${1:-p1}
BASE_URL=${SRE_COPILOT_URL:-http://localhost:8000}
ENDPOINT="$BASE_URL/webhooks/pagerduty"

# Load .env if it exists
if [ -f ".env" ]; then
  export $(grep -v '^#' .env | grep -v '^$' | xargs)
fi

case "$SEVERITY" in
  p1)
    TITLE="HIGH CPU: api-server CPU usage at 95% for 10 minutes"
    DESCRIPTION="CPU usage has exceeded 90% sustained for 10 minutes on api-server-prod-1. All 4 cores are saturated. Request latency has increased 3x."
    URGENCY="high"
    INCIDENT_ID="P1TEST$(date +%s)"
    ;;
  p2)
    TITLE="Elevated error rate: payment-service 5xx errors at 8%"
    DESCRIPTION="Error rate on payment-service has risen to 8% over the last 5 minutes, up from baseline of 0.1%. POST /api/checkout is returning 503."
    URGENCY="high"
    INCIDENT_ID="P2TEST$(date +%s)"
    ;;
  p3)
    TITLE="SSL certificate expiring in 14 days: api.example.com"
    DESCRIPTION="The TLS certificate for api.example.com will expire in 14 days. Renewal is required to prevent downtime."
    URGENCY="low"
    INCIDENT_ID="P3TEST$(date +%s)"
    ;;
  *)
    echo "Usage: $0 [p1|p2|p3]"
    exit 1
    ;;
esac

FIRED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

PAYLOAD=$(cat <<EOF
{
  "messages": [
    {
      "event": {
        "event_type": "incident.triggered",
        "data": {
          "id": "$INCIDENT_ID",
          "number": 9999,
          "title": "$TITLE",
          "description": "$DESCRIPTION",
          "status": "triggered",
          "urgency": "$URGENCY",
          "created_at": "$FIRED_AT",
          "service": {
            "name": "api-server"
          },
          "labels": {},
          "annotations": {}
        }
      }
    }
  ]
}
EOF
)

# Compute HMAC if secret is set
EXTRA_HEADERS=""
if [ -n "${PAGERDUTY_WEBHOOK_SECRET:-}" ]; then
  SIG=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$PAGERDUTY_WEBHOOK_SECRET" | awk '{print $2}')
  EXTRA_HEADERS="-H 'X-PagerDuty-Signature: v1=$SIG'"
  echo "HMAC signature computed: v1=$SIG"
else
  echo "Warning: PAGERDUTY_WEBHOOK_SECRET not set — sending without HMAC signature"
fi

echo "Sending $SEVERITY test alert to $ENDPOINT..."
echo "Incident ID: $INCIDENT_ID"
echo ""

RESPONSE=$(curl -s -w "\n%{http_code}" \
  -X POST \
  -H "Content-Type: application/json" \
  ${EXTRA_HEADERS} \
  -d "$PAYLOAD" \
  "$ENDPOINT")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n -1)

echo "Response: $BODY"
echo "Status:   $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
  echo ""
  echo "✓ Alert accepted. Check #incidents in Slack for the triage result."
else
  echo ""
  echo "✗ Alert rejected with HTTP $HTTP_CODE"
  exit 1
fi
