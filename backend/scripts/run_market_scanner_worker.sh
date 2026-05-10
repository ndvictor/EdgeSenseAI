#!/usr/bin/env sh
set -eu
cd /app
exec python -m app.workers.market_scanner_worker
