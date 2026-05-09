#!/usr/bin/env bash
set -euo pipefail

BACKEND_URL="${1:-${BACKEND_URL:-}}"
if [[ -z "$BACKEND_URL" ]]; then
  echo "Usage: $0 https://<azure-backend-fqdn>   (or set BACKEND_URL env var)" >&2
  exit 1
fi

BASE="${BACKEND_URL%/}"

check() {
  local path="$1"
  echo "GET $BASE$path"
  curl -fsS "$BASE$path" >/dev/null
}

check "/health"
check "/api/workflow-runbook/latest"
check "/api/agent-runtime/status"
check "/api/qlib/status"
check "/api/lab/inventory"

echo "OK: health checks passed."
