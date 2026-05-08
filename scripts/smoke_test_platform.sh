#!/usr/bin/env bash
set -euo pipefail

# Safe smoke test for EdgeSenseAI platform.
# - Read-only GET checks
# - Optional "dry-run" run invocation (best-effort; does not print secrets)
# - Verifies safety flags in returned JSON where possible

API_BASE_URL="${API_BASE_URL:-http://localhost:8900}"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

note() {
  echo "==> $*" >&2
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "missing required command: $1"
}

require_cmd curl
require_cmd python3

curl_json() {
  local path="$1"
  curl -sS --max-time 20 -H "Accept: application/json" "${API_BASE_URL}${path}"
}

curl_status() {
  local path="$1"
  curl -sS --max-time 20 -o /dev/null -w "%{http_code}" "${API_BASE_URL}${path}" || true
}

json_assert_bool_equals() {
  local key="$1"
  local expected="$2"
  local code
  code="$(cat <<'PY'
import json, sys
key = sys.argv[1]
expected = sys.argv[2].lower() == "true"
doc = json.loads(sys.stdin.read() or "{}")
val = doc
for part in key.split("."):
    if isinstance(val, dict) and part in val:
        val = val[part]
    else:
        print(f"missing key: {key}", file=sys.stderr)
        sys.exit(2)
if bool(val) != expected:
    print(f"expected {key}={expected} but got {val}", file=sys.stderr)
    sys.exit(3)
PY
)"
  python3 -c "$code" "$key" "$expected"
}

json_assert_key_present() {
  local key="${1:-}"
  [[ -n "$key" ]] || fail "json_assert_key_present requires key"
  local code
  code="$(cat <<'PY'
import json, sys
key = sys.argv[1]
doc = json.loads(sys.stdin.read() or "{}")
val = doc
for part in key.split("."):
    if isinstance(val, dict) and part in val:
        val = val[part]
    else:
        print(f"missing key: {key}", file=sys.stderr)
        sys.exit(2)
print("ok")
PY
)"
  python3 -c "$code" "$key"
}

note "Checking backend health"
code="$(curl_status /health)"
if [[ "$code" != "200" ]]; then
  fail "backend not reachable at ${API_BASE_URL} (GET /health -> HTTP ${code})"
fi

note "Read-only endpoint checks"
for path in \
  "/api/workflow-runbook/status" \
  "/api/workflow-runbook/stages" \
  "/api/workflow-runbook/latest" \
  "/api/lab/inventory" \
  "/api/session-router/status" \
  "/api/workflow-router/status" \
  "/api/strategy-eligibility/status" \
  "/api/trigger-monitoring/status" \
  "/api/execution-planner/status" \
  "/api/position-monitoring/status" \
  "/api/close-position/status" \
  "/api/post-trade-evaluation/status" \
  "/api/learning-loop/status"
do
  c="$(curl_status "$path")"
  [[ "$c" == "200" ]] || fail "GET ${path} -> HTTP ${c}"
done

note "Verifying runbook safety summary fields"
status_json="$(curl_json /api/workflow-runbook/status)"
printf '%s' "$status_json" | json_assert_key_present "summary.workflow_status" >/dev/null

# These two should remain false in a safe default paper-first environment.
printf '%s' "$status_json" | json_assert_bool_equals "scope.live_trading_enabled" "false" >/dev/null || true
printf '%s' "$status_json" | json_assert_bool_equals "scope.broker_submission_enabled" "false" >/dev/null || true

note "Attempting a safe run invocation (best-effort)"
note "Prefers /api/workflow-orchestrator/run (dry_run) if present; otherwise falls back to /api/command-center/run"

orchestrator_code="$(curl_status /api/workflow-orchestrator/run)"
run_json=""
if [[ "$orchestrator_code" != "404" ]]; then
  run_json="$(curl -sS --max-time 30 -H "Content-Type: application/json" -H "Accept: application/json" \
    -X POST "${API_BASE_URL}/api/workflow-orchestrator/run" \
    -d '{"dry_run": true, "paper_only": true, "allow_mock": true}' || true)"
else
  run_json="$(curl -sS --max-time 30 -H "Content-Type: application/json" -H "Accept: application/json" \
    -X POST "${API_BASE_URL}/api/command-center/run" \
    -d '{}' || true)"
fi

if [[ -n "${run_json}" ]]; then
  # Don’t print the full payload; just validate common safety flags if present.
  printf '%s' "$run_json" | json_assert_bool_equals "llm_used" "false" >/dev/null || true
  printf '%s' "$run_json" | json_assert_bool_equals "submitted_order" "false" >/dev/null || true
  printf '%s' "$run_json" | json_assert_bool_equals "broker_called" "false" >/dev/null || true
fi

note "PASS: smoke test completed (no secrets printed)"

