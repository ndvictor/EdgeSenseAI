# Day Trading route migration table

This table maps **legacy allowlisted** operator endpoints to the **Day Trading v1** namespace (`/api/v1/daytrading/*`). Legacy routes remain available for existing UIs; new surfaces should call v1 only.

| Legacy (still allowlisted in production) | Day Trading v1 |
|------------------------------------------|----------------|
| `GET /health` (bundled) | `GET /api/v1/daytrading/status` → `health` |
| `GET /api/platform-readiness/status` (bundled) | `GET /api/v1/daytrading/status` → `platform_readiness` |
| `GET /api/final-readiness/status` (bundled) | `GET /api/v1/daytrading/status` → `final_readiness` |
| `POST /api/workflow-orchestrator/run` | `POST /api/v1/daytrading/workflow/run` |
| `GET /api/workflow-orchestrator/latest` | `GET /api/v1/daytrading/workflow/latest` |
| `GET /api/worker-status/latest` | `GET /api/v1/daytrading/workers/latest` |
| `GET /api/worker-status/latest` (scanner projection) | `GET /api/v1/daytrading/scanner/latest` |
| `POST /api/scanner/run` | `POST /api/v1/daytrading/scanner/run` |
| `GET /api/promotion/strategies/status` | `GET /api/v1/daytrading/evidence/strategies` |
| `GET /api/promotion/models/status` | `GET /api/v1/daytrading/evidence/models` |
| _(derived from latest orchestrator run)_ | `GET /api/v1/daytrading/recommendation/latest` |
| _(derived from latest orchestrator run)_ | `GET /api/v1/daytrading/risk/status` |
| `GET /api/platform-readiness/status` + latest workflow safety fields | `GET /api/v1/daytrading/execution-boundary` |
| _(n/a)_ | `GET /api/v1/daytrading/contracts/routes` (registry) |

## Not migrated (intentionally)

Legacy exploratory or wide-area APIs remain **blocked in production** unless separately allowlisted. Examples: `/api/command-center`, `/api/live-watchlist/latest`, `/api/edge-signals/latest`, `/api/market/snapshots`, `/api/features/*`, `/api/model-pipeline/*`, `/api/candidate-universe/*`, `/api/universe-selection/*`. Day Trading v1 **must not** call these.

## Frontend

- **New dashboard only:** `frontend/src/app/daytrading-workflow/new/[[...section]]/page.tsx` uses **only** `/api/v1/daytrading/*`.
- **Legacy dashboard:** `frontend/src/app/daytrading-workflow/page.tsx` is unchanged.

## Registry

Authoritative machine-readable list: `GET /api/v1/daytrading/contracts/routes`  
Static mirror: `backend/app/api/route_contracts/daytrading.py` (`DAYTRADING_V1_ROUTE_CONTRACTS`).
