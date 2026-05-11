#!/usr/bin/env bash
# Build a fresh backend image, push to ACR, update the Azure Container App, and
# refresh scheduled worker jobs to the same image tag.
#
# Prerequisites: az CLI, docker, logged in (`az login`), Docker logged into ACR.
#
# Required:
#   DATABASE_URL   (e.g. Supabase Postgres URL)
#
# Common overrides (defaults suit a single RG + shared ACR):
#   RESOURCE_GROUP=edgesenseai-rg
#   LOCATION=centralus
#   ACR_NAME=edgesenseaiacr
#   CONTAINER_APP_NAME=edgesenseai-backend
#   CONTAINER_APP_ENV=edgesenseai-env
#   IMAGE_NAME=edgesenseai-backend
#   IMAGE_TAG=...           (default: short git SHA, or manual-<timestamp>)
#   CORS_ORIGINS=...        (only used if --create-app is passed)
#
# Usage from repo root:
#   DATABASE_URL='postgresql://...' ./scripts/azure-deploy-backend-and-workers.sh
#
# First-time backend (no Container App yet):
#   DATABASE_URL='...' CORS_ORIGINS='https://yourapp.com' \
#     ./scripts/azure-deploy-backend-and-workers.sh --create-app
#
# Dev naming from docs/AZURE_DEV_BACKEND.md (override defaults):
#   RESOURCE_GROUP=edgesenseai-dev-rg CONTAINER_APP_ENV=edgesenseai-dev-env \
#   CONTAINER_APP_NAME=edgesenseai-backend-dev ACR_NAME=<your-acr> \
#   DATABASE_URL='...' ./scripts/azure-deploy-backend-and-workers.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

CREATE_APP=false
for arg in "$@"; do
  if [[ "$arg" == "--create-app" ]]; then
    CREATE_APP=true
  fi
done

RESOURCE_GROUP="${RESOURCE_GROUP:-edgesenseai-rg}"
LOCATION="${LOCATION:-centralus}"
ACR_NAME="${ACR_NAME:-edgesenseaiacr}"
CONTAINER_APP_ENV="${CONTAINER_APP_ENV:-edgesenseai-env}"
CONTAINER_APP_NAME="${CONTAINER_APP_NAME:-edgesenseai-backend}"
IMAGE_NAME="${IMAGE_NAME:-edgesenseai-backend}"
IMAGE_TAG="${IMAGE_TAG:-}"
DATABASE_URL="${DATABASE_URL:-}"
CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:3000}"

if [[ -z "$IMAGE_TAG" ]]; then
  IMAGE_TAG="$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || true)"
fi
if [[ -z "$IMAGE_TAG" ]]; then
  IMAGE_TAG="manual-$(date +%Y%m%d%H%M%S)"
fi

if [[ -z "$DATABASE_URL" ]]; then
  echo "ERROR: DATABASE_URL is required (e.g. export DATABASE_URL='postgresql://...')." >&2
  exit 1
fi

echo "Using IMAGE_TAG=$IMAGE_TAG RESOURCE_GROUP=$RESOURCE_GROUP CONTAINER_APP_NAME=$CONTAINER_APP_NAME"

az extension add --name containerapp --upgrade >/dev/null

echo "Ensuring resource group exists..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" >/dev/null

echo "Ensuring ACR exists..."
if ! az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
  az acr create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$ACR_NAME" \
    --sku Basic \
    --admin-enabled true >/dev/null
fi

ACR_LOGIN_SERVER="$(az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query loginServer -o tsv)"
FULL_IMAGE="$ACR_LOGIN_SERVER/$IMAGE_NAME:$IMAGE_TAG"
echo "ACR image: $FULL_IMAGE"

echo "Logging Docker into ACR..."
az acr login --name "$ACR_NAME" >/dev/null

echo "Building image..."
docker build -f backend/Dockerfile -t "$FULL_IMAGE" backend

echo "Pushing image..."
docker push "$FULL_IMAGE"

_link_registry_to_app() {
  local app="$1"
  if [[ "$(az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query adminUserEnabled -o tsv 2>/dev/null)" == "true" ]]; then
    local reg_user reg_pass
    reg_user="$(az acr credential show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query username -o tsv)"
    reg_pass="$(az acr credential show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query 'passwords[0].value' -o tsv)"
    az containerapp registry set \
      --name "$app" \
      --resource-group "$RESOURCE_GROUP" \
      --server "$ACR_LOGIN_SERVER" \
      --username "$reg_user" \
      --password "$reg_pass" \
      >/dev/null
  fi
}

APP_EXISTS=false
if az containerapp show --name "$CONTAINER_APP_NAME" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
  APP_EXISTS=true
fi

if [[ "$APP_EXISTS" == false && "$CREATE_APP" != true ]]; then
  echo "ERROR: Container app '$CONTAINER_APP_NAME' not found in $RESOURCE_GROUP." >&2
  echo "Run once with --create-app (and set CORS_ORIGINS for production)." >&2
  exit 1
fi

if [[ "$APP_EXISTS" == false ]]; then
  echo "Creating Container Apps environment (if missing)..."
  az containerapp env create \
    --name "$CONTAINER_APP_ENV" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" >/dev/null 2>&1 || true

  echo "Creating Container App $CONTAINER_APP_NAME..."
  REG_ARGS=(--registry-server "$ACR_LOGIN_SERVER")
  if [[ "$(az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query adminUserEnabled -o tsv 2>/dev/null)" == "true" ]]; then
    ACR_USER="$(az acr credential show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query username -o tsv)"
    ACR_PASS="$(az acr credential show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query 'passwords[0].value' -o tsv)"
    REG_ARGS+=(--registry-username "$ACR_USER" --registry-password "$ACR_PASS")
  else
    echo "WARN: ACR admin user not enabled; if create fails, enable admin on ACR or attach a managed identity." >&2
  fi
  az containerapp create \
    --name "$CONTAINER_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --environment "$CONTAINER_APP_ENV" \
    --image "$FULL_IMAGE" \
    --target-port 8900 \
    --ingress external \
    "${REG_ARGS[@]}" \
    --env-vars \
      PORT=8900 \
      APP_ENV=production \
      DATABASE_URL="$DATABASE_URL" \
      CORS_ORIGINS="$CORS_ORIGINS" \
      WORKFLOW_ENABLED=true \
      PAPER_TRADING_ENABLED=true \
      LIVE_TRADING_ENABLED=false \
      BROKER_EXECUTION_ENABLED=false \
      QLIB_EXECUTION_ENABLED=false \
      REQUIRE_HUMAN_APPROVAL=true \
    >/dev/null
else
  echo "Updating Container App image..."
  _link_registry_to_app "$CONTAINER_APP_NAME" || true
  az containerapp update \
    --name "$CONTAINER_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --image "$FULL_IMAGE" \
    >/dev/null
fi

FQDN="$(az containerapp show --name "$CONTAINER_APP_NAME" --resource-group "$RESOURCE_GROUP" --query properties.configuration.ingress.fqdn -o tsv)"
echo "Backend URL: https://$FQDN"

echo "Updating worker jobs to $FULL_IMAGE ..."
export RESOURCE_GROUP
export CONTAINER_APP_ENV
export ACR_LOGIN_SERVER
export IMAGE_NAME
export IMAGE_TAG
export DATABASE_URL
bash "$REPO_ROOT/scripts/azure-create-workers.sh"

echo "Done. Backend revision should be active; jobs will use the new image on their next scheduled run."
echo "Optional: az containerapp job start --name edgesenseai-market-scan-job --resource-group $RESOURCE_GROUP"
