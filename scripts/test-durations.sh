#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../backend"
PYTHONPATH=. pytest -q --durations=25 --durations-min=0.1
