#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_ENV="${ROOT_DIR}/backend/.env"

if [[ -f "${BACKEND_ENV}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${BACKEND_ENV}"
  set +a
fi

export ALPACA_API_KEY="${ALPACA_API_KEY:-${ALPACA_API_KEY_ID:-${APCA_API_KEY_ID:-}}}"
export ALPACA_SECRET_KEY="${ALPACA_SECRET_KEY:-${ALPACA_API_SECRET_KEY:-${APCA_API_SECRET_KEY:-}}}"
export ALPACA_PAPER_TRADE="${ALPACA_PAPER_TRADE:-true}"

if [[ -z "${ALPACA_API_KEY}" || -z "${ALPACA_SECRET_KEY}" ]]; then
  echo "Missing ALPACA_API_KEY or ALPACA_SECRET_KEY. Add them to backend/.env before starting Alpaca MCP." >&2
  exit 1
fi

# Check if stdin is a terminal or closed (nohup/background)
if [[ ! -t 0 ]]; then
  # Stdin is closed (nohup/background) - provide dummy input
  exec 0< <(tail -f /dev/null)
fi

# Show warning if running interactively
if [[ -t 0 ]]; then
  echo "⚠️  WARNING: MCP server is running. DO NOT TYPE in this terminal!"
  echo "   Use Ctrl+C to stop. Open a new terminal for commands."
  echo ""
fi

exec uvx alpaca-mcp-server
