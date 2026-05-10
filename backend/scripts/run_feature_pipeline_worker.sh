#!/usr/bin/env sh
set -eu
cd /app
exec python -m app.workers.feature_pipeline_worker
