#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(dirname "$0")/.."
cd "$ROOT_DIR/backend"
python -m compileall app
PYTHONPATH=. pytest -q

if [ -d "$ROOT_DIR/frontend" ]; then
  cd "$ROOT_DIR/frontend"
  npx tsc --noEmit
  npm run build
fi
