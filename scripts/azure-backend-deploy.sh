#!/usr/bin/env bash
set -euo pipefail

# Safe template. Fill these in before running.
RESOURCE_GROUP="${RESOURCE_GROUP:-edgesenseai-rg}"
LOCATION="${LOCATION:-eastus}"
ACR_NAME="${ACR_NAME:-edgesenseaiacr}"
CONTAINER_APP_ENV="${CONTAINER_APP_ENV:-edgesenseai-env}"
CONTAINER_APP_NAME="${CONTAINER_APP_NAME:-edgesenseai-backend}"
IMAGE_NAME="${IMAGE_NAME:-edgesenseai-backend}"
IMAGE_TAG="${IMAGE_TAG:-v1}"

# Required for real deployments
DATABASE_URL="${DATABASE_URL:-}"
CORS_ORIGINS="${CORS_ORIGINS:-}"

if [[ -z "$DATABASE_URL" ]]; then
  echo "ERROR: DATABASE_URL is required (e.g. Supabase Postgres)." >&2
  exit 1
fi
if [[ -z "$CORS_ORIGINS" ]]; then
  echo "ERROR: CORS_ORIGINS is required (comma-separated Vercel origins)." >&2
  exit 1
fi

az group create --name "$RESOURCE_GROUP" --location "$LOCATION" >/dev/null

ACR_LOGIN_SERVER="$(az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query loginServer -o tsv)"
echo "Using ACR: $ACR_LOGIN_SERVER"

echo "Creating/ensuring Container Apps environment..."
az containerapp env create \
  --name "$CONTAINER_APP_ENV" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" >/dev/null || true

echo "Deploying Container App..."
az containerapp create \
  --name "$CONTAINER_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$CONTAINER_APP_ENV" \
  --image "$ACR_LOGIN_SERVER/$IMAGE_NAME:$IMAGE_TAG" \
  --target-port 8900 \
  --ingress external \
  --registry-server "$ACR_LOGIN_SERVER" \
  --env-vars \
    PORT=8900 \
    APP_ENV=production \
    DATABASE_URL="$DATABASE_URL" \
    CORS_ORIGINS="$CORS_ORIGINS" \
    LIVE_TRADING_ENABLED=false \
    BROKER_EXECUTION_ENABLED=false >/dev/null

FQDN="$(az containerapp show --name "$CONTAINER_APP_NAME" --resource-group "$RESOURCE_GROUP" --query properties.configuration.ingress.fqdn -o tsv)"
echo "Deployed. FQDN: https://$FQDN"
echo "Health: curl -fsS \"https://$FQDN/health\""
