# Azure Container Apps deployment (backend)

This guide deploys the **FastAPI backend only** to **Azure Container Apps**.

## Prereqs

- Azure CLI installed: `az version`
- Logged in: `az login`
- Docker available locally (or use ACR build tasks)
- Your backend listens on `PORT` (default `8900`) and exposes `/health`

## Variables

Set these once in your shell:

```bash
RESOURCE_GROUP="edgesenseai-rg"
LOCATION="centralus"
ACR_NAME="edgesenseaiacr"          # must be globally unique, lowercase, 5-50 chars
CONTAINER_APP_ENV="edgesenseai-env"
CONTAINER_APP_NAME="edgesenseai-backend"
IMAGE_NAME="edgesenseai-backend"
IMAGE_TAG="v1"
```

## 1) Create resource group

```bash
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"
```

## 2) Create Azure Container Registry (ACR)

```bash
az acr create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$ACR_NAME" \
  --sku Basic \
  --admin-enabled true
```

Get the login server:

```bash
ACR_LOGIN_SERVER="$(az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query loginServer -o tsv)"
echo "$ACR_LOGIN_SERVER"
```

Login Docker to ACR:

```bash
az acr login --name "$ACR_NAME"
```

## 3) Build + push image

Local build (from repo root):

```bash
docker build -f backend/Dockerfile -t "$ACR_LOGIN_SERVER/$IMAGE_NAME:$IMAGE_TAG" backend
docker push "$ACR_LOGIN_SERVER/$IMAGE_NAME:$IMAGE_TAG"
```

## 4) Create Container Apps environment

```bash
az containerapp env create \
  --name "$CONTAINER_APP_ENV" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION"
```

## 5) Deploy the backend as a Container App

The backend reads `PORT` (default `8900`), and uses `DATABASE_URL` from env.
Production persistence requires a real managed Postgres `DATABASE_URL`. Do not deploy production with a missing URL or a localhost URL; Postgres is the source of truth for durable workflow state.

```bash
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
    ENVIRONMENT=production \
    APP_ENV=production \
    DATABASE_URL="__REPLACE_WITH_SUPABASE_OR_AZURE_POSTGRES_URL__" \
    CORS_ORIGINS="__REPLACE_WITH_VERCEL_ORIGINS__" \
    MARKET_DATA_MODE=provider \
    ALLOW_MOCK_MARKET_DATA=false \
    ALLOW_SYNTHETIC_MARKET_DATA=false \
    QLIB_REQUIRED=false \
    LIVE_TRADING_ENABLED=false \
    BROKER_EXECUTION_ENABLED=false
```

Notes:
- `DATABASE_URL` is required for production persistence and must point to managed Postgres, not localhost.
- `MARKET_DATA_MODE=provider` is required for production workflow runs.
- Mock and synthetic market data are disabled in production with `ALLOW_MOCK_MARKET_DATA=false` and `ALLOW_SYNTHETIC_MARKET_DATA=false`.
- Qlib is optional unless a selected strategy explicitly requires it; keep `QLIB_REQUIRED=false` for the paper-first workflow.
- Redis is **optional but recommended**. If you have one, add `REDIS_URL=...`.
- Missing provider keys (Alpaca/Polygon/News/Qlib runtime) should yield **blocked/unconfigured** statuses in endpoints, not crash startup.

## 6) Verify endpoints

Get the public FQDN:

```bash
FQDN="$(az containerapp show --name "$CONTAINER_APP_NAME" --resource-group "$RESOURCE_GROUP" --query properties.configuration.ingress.fqdn -o tsv)"
echo "$FQDN"
```

Health:

```bash
curl -fsS "https://$FQDN/health"
```

Workflow runbook latest:

```bash
curl -fsS "https://$FQDN/api/workflow-runbook/latest"
```

Agent runtime status:

```bash
curl -fsS "https://$FQDN/api/agent-runtime/status"
```

Qlib status (safe even if unavailable):

```bash
curl -fsS "https://$FQDN/api/qlib/status"
```

## Local Docker run (sanity)

From repo root:

```bash
docker build -f backend/Dockerfile -t edgesenseai-backend:local backend

docker run --rm -p 8900:8900 \
  -e PORT=8900 \
  -e APP_ENV=local \
  -e DATABASE_URL="postgresql://user:pass@host:5432/dbname" \
  -e CORS_ORIGINS="http://localhost:3900" \
  edgesenseai-backend:local
```

Then:

```bash
curl -fsS http://localhost:8900/health
```

## Risks / common blockers

- **DB connectivity**: `DATABASE_URL` must be reachable from ACA (firewall/VNET rules).
- **CORS**: set `CORS_ORIGINS` to your Vercel frontend URLs.
- **Optional services**: if Redis is not configured/reachable, features should degrade gracefully; the backend should still start.

