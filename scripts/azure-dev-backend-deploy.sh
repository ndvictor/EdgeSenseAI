#!/usr/bin/env bash
set -euo pipefail

# Variables (edit or export before running)
RESOURCE_GROUP="${RESOURCE_GROUP:-edgesenseai-dev-rg}"
LOCATION="${LOCATION:-centralus}"
APP_NAME="${APP_NAME:-edgesenseai-backend-dev}"
ENV_NAME="${ENV_NAME:-edgesenseai-dev-env}"

DATABASE_URL="${DATABASE_URL:-}"
CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:3000}"

if [[ -z "$DATABASE_URL" ]]; then
  echo "ERROR: DATABASE_URL is required (Supabase Postgres URL)." >&2
  exit 1
fi

az extension add --name containerapp --upgrade >/dev/null

echo "Deploying backend to Azure Container Apps (build from ./backend)..."
az containerapp up \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --environment "$ENV_NAME" \
  --source ./backend \
  --ingress external \
  --target-port 8900

echo "Setting dev env vars..."
az containerapp update \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --set-env-vars \
    PORT=8900 \
    DATABASE_URL="$DATABASE_URL" \
    CORS_ORIGINS="$CORS_ORIGINS" \
    WORKFLOW_ENABLED=true \
    PAPER_TRADING_ENABLED=true \
    LIVE_TRADING_ENABLED=false \
    BROKER_EXECUTION_ENABLED=false \
    QLIB_EXECUTION_ENABLED=false \
    REQUIRE_HUMAN_APPROVAL=true >/dev/null

BACKEND_FQDN="$(az containerapp show \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query properties.configuration.ingress.fqdn \
  -o tsv)"

echo "Backend URL: https://$BACKEND_FQDN"
echo "Set frontend: NEXT_PUBLIC_API_URL=https://$BACKEND_FQDN"
