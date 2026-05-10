#!/usr/bin/env bash
set -euo pipefail

# Safe Phase 6 smoke test for the EdgeSenseAI autonomous day-trading platform.
# It exercises visibility/control endpoints and one dry-run orchestrator request.
# It must never submit broker orders, enable live trading, or call LLM decisioning.

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
  curl -sS --max-time 30 -H "Accept: application/json" "${API_BASE_URL}${path}"
}

curl_status() {
  local path="$1"
  curl -sS --max-time 30 -o /dev/null -w "%{http_code}" "${API_BASE_URL}${path}" || true
}

post_json() {
  local path="$1"
  local payload="$2"
  curl -sS --max-time 60 -H "Content-Type: application/json" -H "Accept: application/json" \
    -X POST "${API_BASE_URL}${path}" \
    -d "${payload}"
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

json_assert_run_contract() {
  local code
  code="$(cat <<'PY'
import json, sys

doc = json.loads(sys.stdin.read() or "{}")
run = doc.get("run") if isinstance(doc.get("run"), dict) else doc
if not isinstance(run, dict):
    print("missing run object", file=sys.stderr)
    sys.exit(2)

def require_key(key):
    if key not in run:
        print(f"missing run key: {key}", file=sys.stderr)
        sys.exit(3)
    return run[key]

def require_false(key):
    value = require_key(key)
    if bool(value) is not False:
        print(f"expected {key}=false but got {value!r}", file=sys.stderr)
        sys.exit(4)

def require_non_empty_list(key):
    value = require_key(key)
    if not isinstance(value, list) or not value:
        print(f"expected non-empty list for {key}, got {value!r}", file=sys.stderr)
        sys.exit(5)

def require_present_any(keys, label):
    if not any(key in run for key in keys):
        print(f"missing {label}: expected one of {keys}", file=sys.stderr)
        sys.exit(6)

require_key("workflow_run_id")
require_key("orchestrator_run_id")
require_non_empty_list("stage_timeline")

for key in ("allow_submit", "approval_required"):
    require_key(key)

if bool(run["allow_submit"]):
    print("allow_submit must be false", file=sys.stderr)
    sys.exit(8)

require_false("submitted_order")
require_false("broker_called")
require_false("llm_used")

if run.get("source_mode") != "runtime":
    print(f"expected source_mode=runtime but got {run.get('source_mode')!r}", file=sys.stderr)
    sys.exit(9)
if bool(run.get("using_non_real_data")):
    print("runtime source silently became non-real data", file=sys.stderr)
    sys.exit(9)

for key in ("provider_status", "feature_store_status", "persistence_status", "freshness_status", "kafka_status"):
    require_key(key)
for key in ("qlib_available", "proof_status", "evidence_blockers", "evidence_warnings"):
    require_key(key)
for key in ("small_account_decision", "max_risk_dollars", "max_daily_loss_dollars", "feasible_symbols", "small_account_blockers", "small_account_warnings"):
    require_key(key)

if run.get("qlib_available") is False and run.get("status") == "failed":
    print("Qlib unavailable should not fail the workflow", file=sys.stderr)
    sys.exit(10)
if "optional" not in str(run.get("kafka_status", "")).lower():
    print(f"Kafka status should remain optional, got {run.get('kafka_status')!r}", file=sys.stderr)
    sys.exit(11)

supported = run.get("supported_horizons") or []
if supported != ["day_trading"]:
    print(f"expected supported_horizons=['day_trading'], got {supported!r}", file=sys.stderr)
    sys.exit(12)
if run.get("current_horizon") == "swing_trading" or run.get("horizon") == "swing_trading":
    print("swing_trading appeared as active workflow scope", file=sys.stderr)
    sys.exit(12)

print("ok")
PY
)"
  python3 -c "$code"
}

note "Checking backend health"
code="$(curl_status /health)"
[[ "$code" == "200" ]] || fail "backend not reachable at ${API_BASE_URL} (GET /health -> HTTP ${code})"

note "Checking Phase 3-6 platform endpoints"
for path in \
  "/api/final-readiness/status" \
  "/api/platform-readiness/status" \
  "/api/agent-runtime/status" \
  "/api/qlib/status" \
  "/api/proof-registry/status" \
  "/api/model-evidence/status" \
  "/api/strategy-evidence/status" \
  "/api/workflow-governance/status" \
  "/api/workflow-orchestrator/latest" \
  "/api/approval-queue/status" \
  "/api/approval-queue/items" \
  "/api/audit-log/status" \
  "/api/audit-log/events" \
  "/api/workflow-scheduler/status" \
  "/api/lab/inventory"
do
  c="$(curl_status "$path")"
  [[ "$c" == "200" ]] || fail "GET ${path} -> HTTP ${c}"
done

note "Verifying final readiness safety fields"
final_json="$(curl_json /api/final-readiness/status)"
printf '%s' "$final_json" | json_assert_key_present "platform_completion.agent_runtime_complete" >/dev/null
printf '%s' "$final_json" | json_assert_bool_equals "safety.no_default_broker_submit" "true" >/dev/null
printf '%s' "$final_json" | json_assert_bool_equals "safety.no_default_live_trading" "true" >/dev/null
printf '%s' "$final_json" | json_assert_bool_equals "safety.no_llm_decisioning" "true" >/dev/null

note "Running dry-run orchestrator workflow"
run_json="$(post_json /api/workflow-orchestrator/run '{
  "workflow_name": "US Stock Day-Trading Paper Workflow v1",
  "asset_class": "stock",
  "horizon": "day_trading",
  "mode": "paper_first",
  "source": "runtime",
  "symbols": [],
  "max_candidates": 5,
  "stop_at_stage": 9,
  "dry_run": true,
  "require_human_approval": true,
  "allow_submit": false,
  "simulated_position": false,
  "simulated_closed_trade": false,
  "metadata": {"smoke_test": true}
}')"

printf '%s' "$run_json" | json_assert_run_contract >/dev/null

note "Checking post-run operational surfaces"
for path in \
  "/api/approval-queue/items" \
  "/api/audit-log/events" \
  "/api/workflow-scheduler/status"
do
  c="$(curl_status "$path")"
  [[ "$c" == "200" ]] || fail "GET ${path} -> HTTP ${c}"
done

note "PASS: platform smoke test completed with broker_called=false, submitted_order=false, llm_used=false"
