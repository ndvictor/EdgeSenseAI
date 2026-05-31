#!/usr/bin/env bash
# Build az containerapp --set-env-vars arguments for paper_auto production.
# Used by GitHub Actions and manual Azure deploys. Live broker submit stays off.
set -euo pipefail

CORS_ORIGINS="${CORS_ORIGINS:-https://edge-sense-ai.vercel.app,http://localhost:3900,http://127.0.0.1:3900}"
MARKET_DATA_PROVIDER_PRIORITY="${MARKET_DATA_PROVIDER_PRIORITY:-alpaca,polygon,yfinance}"

# Core gates (match backend/runtime_settings.json baked into the image)
ENV_PAIRS=(
  "ENVIRONMENT=production"
  "APP_ENV=production"
  "WORKFLOW_ENABLED=true"
  "PAPER_TRADING_ENABLED=true"
  "LIVE_TRADING_ENABLED=false"
  "BROKER_EXECUTION_ENABLED=true"
  "REQUIRE_HUMAN_APPROVAL=false"
  "EXECUTION_MODE=paper"
  "OWNER_AUTHORITY_LEVEL=paper_auto"
  "AGENT_REASONING_ENABLED=true"
  "AGENT_CAN_RECOMMEND_TRADES=true"
  "AGENT_CAN_CREATE_PAPER_PLANS=true"
  "AGENT_CAN_CREATE_APPROVAL_REQUESTS=true"
  "AGENT_CAN_SUBMIT_PAPER_ORDERS=true"
  "AGENT_CAN_AUTO_SUBMIT_PAPER_ORDERS=true"
  "AGENT_CAN_SUBMIT_LIVE_ORDERS=false"
  "MARKET_DATA_MODE=provider"
  "MARKET_DATA_PROVIDER=alpaca"
  "MARKET_DATA_PROVIDER_PRIORITY=${MARKET_DATA_PROVIDER_PRIORITY}"
  "ALPACA_MARKET_DATA_ENABLED=true"
  "ALLOW_NON_REAL_MARKET_DATA=false"
  "ALLOW_SYNTHETIC_MARKET_DATA=false"
  "QLIB_REQUIRED=false"
  "CORS_ORIGINS=${CORS_ORIGINS}"
)

append_if_set() {
  local key="$1"
  local val="${2:-}"
  if [[ -n "${val// }" ]]; then
    ENV_PAIRS+=("${key}=${val}")
  fi
}

append_if_set "DATABASE_URL" "${DATABASE_URL:-}"
append_if_set "OPS_ADMIN_TOKEN" "${OPS_ADMIN_TOKEN:-}"
append_if_set "ALPACA_API_KEY" "${ALPACA_API_KEY:-}"
append_if_set "ALPACA_SECRET_KEY" "${ALPACA_SECRET_KEY:-}"
append_if_set "ALPACA_PAPER_TRADING_BASE_URL" "${ALPACA_PAPER_TRADING_BASE_URL:-https://paper-api.alpaca.markets}"
append_if_set "ALPACA_BASE_URL" "${ALPACA_BASE_URL:-https://data.alpaca.markets}"

# Print space-separated KEY=VALUE for az CLI (caller must quote if needed)
printf '%s\n' "${ENV_PAIRS[@]}"
