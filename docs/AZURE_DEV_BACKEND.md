# Azure dev backend (Container Apps)

Goal: run the **EdgeSenseAI backend** in **Azure Container Apps** for development. Frontend stays **local only** and points to Azure via `NEXT_PUBLIC_API_URL`.

## 1) Login and set variables

```bash
az login
az extension add --name containerapp --upgrade

RESOURCE_GROUP="edgesenseai-dev-rg"
LOCATION="eastus"
APP_NAME="edgesenseai-backend-dev"
ENV_NAME="edgesenseai-dev-env"
```

## 2) Deploy backend from local source

From repo root:

```bash
az containerapp up \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --environment "$ENV_NAME" \
  --source ./backend \
  --ingress external \
  --target-port 8900
```

This builds from `backend/Dockerfile`, pushes an image, and deploys it to Container Apps.

## 3) Supabase `DATABASE_URL`

Use your Supabase Postgres connection string as `DATABASE_URL` (prefer the **non-pooling** URL unless you know you need pooling).

## 4) Set dev environment variables

Replace the placeholders and run:

```bash
az containerapp update \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --set-env-vars \
    PORT=8900 \
    DATABASE_URL="__SUPABASE_POSTGRES_URL__" \
    CORS_ORIGINS="http://localhost:3000" \
    WORKFLOW_ENABLED=true \
    PAPER_TRADING_ENABLED=true \
    LIVE_TRADING_ENABLED=false \
    BROKER_EXECUTION_ENABLED=false \
    QLIB_EXECUTION_ENABLED=false \
    REQUIRE_HUMAN_APPROVAL=true
```

Redis is optional; skip `REDIS_URL` for now.

## 5) Get the backend URL

```bash
BACKEND_FQDN="$(az containerapp show \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query properties.configuration.ingress.fqdn \
  -o tsv)"

echo "https://$BACKEND_FQDN"
```

## 6) View logs

```bash
az containerapp logs show \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --follow
```

## 7) Redeploy after backend changes

From repo root:

```bash
az containerapp up \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --environment "$ENV_NAME" \
  --source ./backend \
  --ingress external \
  --target-port 8900
```

## 8) Rollback notes

- Container Apps supports revisions. If a deploy breaks, roll back to a prior revision in the Azure Portal (Container App → Revisions).
- Keep `LIVE_TRADING_ENABLED=false` and `BROKER_EXECUTION_ENABLED=false` for dev.

