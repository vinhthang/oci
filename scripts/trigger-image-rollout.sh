#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 3 ]]; then
  echo "Usage: $0 <service> [tag] [digest]" >&2
  echo "Allowed services: vietcalendar, collab-mcp, review-server, attention-metrics-server, ai-incident-commander" >&2
  exit 2
fi

SERVICE="$1"
TAG="${2:-}"
DIGEST="${3:-}"
WEBHOOK_URL="${WEBHOOK_URL:-https://webhook.vinhthang.dev/deploy}"
SECRET="${WEBHOOK_SECRET:-}"

if [[ -z "$SECRET" ]]; then
  SECRET="$(ssh arm10 "/usr/local/bin/kubectl get secret gitops-webhook-secret -n system -o jsonpath='{.data.webhook-secret}' | base64 -d")"
fi

if [[ -z "$SECRET" ]]; then
  echo "ERROR: WEBHOOK_SECRET is empty and could not be read from system/gitops-webhook-secret" >&2
  exit 1
fi

PAYLOAD="$(python3 -c '
import json, sys
svc, tag, digest = sys.argv[1:4]
body = {"service": svc}
if tag:
    body["tag"] = tag
if digest:
    body["digest"] = digest
print(json.dumps(body))
' "$SERVICE" "$TAG" "$DIGEST")"

curl -fsS -X POST "$WEBHOOK_URL" \
  -H "Authorization: Bearer ${SECRET}" \
  -H "Content-Type: application/json" \
  --data-binary "$PAYLOAD"
