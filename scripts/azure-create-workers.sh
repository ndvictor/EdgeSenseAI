#!/usr/bin/env bash
set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-edgesenseai-rg}"
CONTAINER_APP_ENV="${CONTAINER_APP_ENV:-edgesenseai-env}"
LOCATION="${LOCATION:-centralus}"
ACR_LOGIN_SERVER="${ACR_LOGIN_SERVER:-opsenseaiacrbuild.azurecr.io}"
IMAGE_NAME="${IMAGE_NAME:-edgesenseai-backend}"
IMAGE_TAG="${IMAGE_TAG:-cd38f08}"

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL must be supplied in the environment." >&2
  exit 1
fi

IMAGE="$ACR_LOGIN_SERVER/$IMAGE_NAME:$IMAGE_TAG"
ENV_ID="$(az containerapp env show --name "$CONTAINER_APP_ENV" --resource-group "$RESOURCE_GROUP" --query id -o tsv)"
if [[ -z "$ENV_ID" ]]; then
  echo "Container Apps environment not found: $CONTAINER_APP_ENV in $RESOURCE_GROUP" >&2
  exit 1
fi

create_or_update_job() {
  local name="$1"
  local module="$2"
  local schedule="$3"

  local env_args=(
    ENVIRONMENT=production
    APP_ENV=production
    DATABASE_URL="$DATABASE_URL"
    MARKET_DATA_MODE=provider
    MARKET_DATA_PROVIDER=yfinance
    MARKET_DATA_PROVIDER_PRIORITY=polygon,alpaca,yfinance
    ALLOW_MOCK_MARKET_DATA=false
    ALLOW_SYNTHETIC_MARKET_DATA=false
    QLIB_REQUIRED=false
    PAPER_TRADING_ENABLED=true
    LIVE_TRADING_ENABLED=false
    BROKER_EXECUTION_ENABLED=false
    REQUIRE_HUMAN_APPROVAL=true
  )

  echo "Creating/updating job: $name image=$IMAGE location=$LOCATION"
  if az containerapp job show --name "$name" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
    az containerapp job update \
      --name "$name" \
      --resource-group "$RESOURCE_GROUP" \
      --image "$IMAGE" \
      --cpu 1.0 \
      --memory 2Gi \
      --replica-timeout 600 \
      --replica-retry-limit 1 \
      --set-env-vars "${env_args[@]}" \
      --command python \
      --args -m "$module" >/dev/null
  else
    az containerapp job create \
      --name "$name" \
      --resource-group "$RESOURCE_GROUP" \
      --environment "$ENV_ID" \
      --trigger-type Schedule \
      --cron-expression "$schedule" \
      --replica-timeout 600 \
      --replica-retry-limit 1 \
      --image "$IMAGE" \
      --cpu 1.0 \
      --memory 2Gi \
      --env-vars "${env_args[@]}" \
      --command python \
      --args -m "$module" >/dev/null
  fi
}

create_or_update_job "edgesenseai-market-scanner-worker" "app.workers.market_scanner_worker" "*/5 * * * *"
create_or_update_job "edgesenseai-data-ingestion-worker" "app.workers.data_ingestion_worker" "*/5 * * * *"
create_or_update_job "edgesenseai-feature-pipeline-worker" "app.workers.feature_pipeline_worker" "*/5 * * * *"

echo "Worker jobs configured with existing image: $IMAGE"
