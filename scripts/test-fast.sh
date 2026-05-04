#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../backend"
python -m compileall app
PYTHONPATH=. pytest -m "not integration and not slow" -q
