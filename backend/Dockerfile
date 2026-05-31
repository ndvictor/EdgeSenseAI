FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.prod.txt ./requirements.prod.txt

RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install --prefer-binary --no-cache-dir -r requirements.prod.txt

COPY app ./app
COPY scripts ./scripts
COPY runtime_settings.json ./runtime_settings.json
RUN chmod +x /app/scripts/run_market_scanner_worker.sh \
    /app/scripts/run_data_ingestion_worker.sh \
    /app/scripts/run_feature_pipeline_worker.sh

EXPOSE 8900

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -fsS http://127.0.0.1:${PORT:-8900}/health || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8900}"]
