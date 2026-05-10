# Day Trading v1 API contract

Base path: **`/api/v1/daytrading`** (mounted under the FastAPI app with prefix `/api/v1`).

All handlers are **thin wrappers** over existing services (`health_service`, platform readiness, final readiness, worker output store, real scanner diagnostics, promotion center, workflow orchestrator). No HTTP self-calls and no legacy “command-center” or watchlist stacks.

## Conventions

- **JSON** request/response bodies.
- **Production:** routes listed here are on the production allowlist in `backend/app/main.py` (alongside legacy allowlisted routes until those are retired from clients).
- **Errors:** Standard FastAPI HTTP errors; production middleware may return `410` with `legacy_runtime_disabled_real_data_only` for **non-allowlisted** paths (not for these v1 paths).

## Endpoints

### `GET /api/v1/daytrading/status`

Aggregated bundle:

- `health` — same shape as `GET /health` (`get_health_snapshot()`).
- `platform_readiness` — same shape as `GET /api/platform-readiness/status`.
- `final_readiness` — same shape as `GET /api/final-readiness/status`.

### `POST /api/v1/daytrading/scanner/run`

Body (extra fields ignored):

- `strategy_key` (default `stock_day_trading`)
- `symbols` (list; normalized to uppercase)
- `max_candidates` (default `10`)
- `data_source` (default `auto`)
- `auto_run`, `trigger_type`, `trigger_workflow` — accepted for client compatibility; scanner service uses symbols / max_candidates / data_source.

Response: same family as legacy `POST /api/scanner/run` (`scanner_diagnostics`, `status`, safety flags `submitted_order`, `broker_called`, `llm_used`).

### `GET /api/v1/daytrading/scanner/latest`

Scanner-focused projection from `get_latest_worker_output_summary()` (scanner worker, diagnostics, counts, persistence).

### `GET /api/v1/daytrading/workers/latest`

Full worker summary: same payload shape as `GET /api/worker-status/latest` (`{"status":"ok", ...}`).

### `POST /api/v1/daytrading/workflow/run`

Body (extra fields ignored):

- `dry_run` (default `true`)
- `allow_submit` (default `false`)
- `symbols` (list)
- `source` (`runtime` | `manual` | … — forwarded into `OrchestratorRunRequest`)

Response: same envelope as legacy `POST /api/workflow-orchestrator/run` (`status`, `recommendation`, `run`, `blockers`, `warnings`, `broker_called`, `submitted_order`, `llm_used`).

### `GET /api/v1/daytrading/workflow/latest`

`{ "status": "ok", "run": <OrchestratorRunResponse model_dump or null> }`

### `GET /api/v1/daytrading/recommendation/latest`

Subset of alpha/recommendation fields from `get_latest_orchestrator_run()` for dashboard cards.

### `GET /api/v1/daytrading/evidence/strategies`

Same as `GET /api/promotion/strategies/status`.

### `GET /api/v1/daytrading/evidence/models`

Same as `GET /api/promotion/models/status`.

### `GET /api/v1/daytrading/risk/status`

Risk / small-account fields from latest orchestrator run (null-safe when no run exists).

### `GET /api/v1/daytrading/execution-boundary`

- `execution_gates` from platform readiness `systems.execution_gates`.
- `from_latest_workflow`: `broker_called`, `submitted_order`, `allow_submit`, `approval_required`, `llm_used`, `using_non_real_data` from latest run.

### `GET /api/v1/daytrading/contracts/routes`

Returns `DAYTRADING_V1_ROUTE_CONTRACTS` (method, path, legacy_sources, description).

## CORS

Allowed **origins** are configured with `CORS_ORIGINS` (comma-separated), not per-route. Include local and deployed frontend URLs. See `backend/.env.example`.
