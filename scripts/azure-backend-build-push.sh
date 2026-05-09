#!/usr/bin/env bash
set -euo pipefail

# Safe template. Fill these in before running.
RESOURCE_GROUP="${RESOURCE_GROUP:-edgesenseai-rg}"
LOCATION="${LOCATION:-eastus}"
ACR_NAME="${ACR_NAME:-edgesenseaiacr}" # must be globally unique, lowercase
IMAGE_NAME="${IMAGE_NAME:-edgesenseai-backend}"
IMAGE_TAG="${IMAGE_TAG:-v1}"

echo "Ensuring resource group exists..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" >/dev/null

echo "Ensuring ACR exists..."
az acr create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$ACR_NAME" \
  --sku Basic \
  --admin-enabled true >/dev/null || true

ACR_LOGIN_SERVER="$(az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query loginServer -o tsv)"
echo "ACR login server: $ACR_LOGIN_SERVER"

echo "Logging into ACR..."
az acr login --name "$ACR_NAME" >/dev/null

echo "Building image..."
docker build -f backend/Dockerfile -t "$ACR_LOGIN_SERVER/$IMAGE_NAME:$IMAGE_TAG" backend

echo "Pushing image..."
docker push "$ACR_LOGIN_SERVER/$IMAGE_NAME:$IMAGE_TAG"

echo "Done."
