#!/usr/bin/env sh
set -eu
cd /app
exec python -m app.workers.data_ingestion_worker
