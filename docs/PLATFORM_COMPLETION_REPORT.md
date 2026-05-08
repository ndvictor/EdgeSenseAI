# Platform Completion Report (v1)

This report documents the current “platform completion” state for EdgeSenseAI with emphasis on **paper-first, US stock, day-trading** workflows and **visibility-first** UX. It intentionally does **not** grant any automatic broker submission authority.

## Scope & safety baseline (v1)

- **Asset scope**: US stocks only
- **Horizon scope**: day trading only
- **Mode**: paper-first / visibility-first
- **No LLM required** for the stage-spine visibility pages (Stage 3–14)
- **No broker submission by default**
- **Human approval required** before any future execution submission path

## Phases 0–6 (execution plan status)

### Phase 0 — Agent contract (recommended)
- **Status**: recommended hardening item
- **Why**: unify trace, idempotency, and safety boundaries across “run” entrypoints

### Phase 1 — Persisted workflow run state (recommended)
- **Status**: recommended hardening item
- **Why**: current stage-spine “latest” values are predominantly in-process (“latest snapshot”) and are not a durable, replayable state machine.

### Phase 2 — Stage 3–14 visibility spine (complete for UI + API contract)
- **Stage 3**: Session Router (`/session-router`)
- **Stage 5**: Workflow Router (`/workflow-router`)
- **Stage 7**: Strategy Eligibility (`/strategy-eligibility`)
- **Stage 8**: Trigger Monitoring (`/trigger-monitoring`)
- **Stage 9**: Execution Planner (preview only) (`/execution-planner`)
- **Stage 11**: Position Monitoring (`/position-monitoring`)
- **Stage 12**: Close Position review (preview only) (`/close-position`)
- **Stage 13**: Post-Trade Evaluation (`/post-trade-evaluation`)
- **Stage 14**: Learning Loop (recommendations only) (`/learning-loop`)

### Phase 3 — Glue/adapters (partially present)
- **Scanner / candidates / decision-workflow** exist as separate “run” flows (see below).
- **Full automatic handoff** from scanner outputs into the Stage 5→14 spine remains a future integration item.

### Phase 4 — Orchestrator “Run button” (partially present)
- Existing “run” entrypoints include Command Center / decision workflows / strategy workflows / upper workflow runs.
- A unified Stage 1–14 orchestrator that chains the stage spine in a single persisted run is a future item.

### Phase 5 — Observability UI (present)
- **Workflow Runbook** dashboard: `/workflow-runbook` (read-only; no orchestration)
- **Lab Platform** inventory: `/lab` (read-only inventory)

### Phase 6 — Scheduler/queue + approvals queue (future hardening)
- APScheduler scaffolding exists; “configured_not_started” states may exist depending on environment.
- A durable approvals queue for stage handoffs is recommended before any execution automation.

## Key endpoints & routes (visibility and run surfaces)

### Read-only runbook
- `GET /api/workflow-runbook/status`
- `GET /api/workflow-runbook/stages`
- `GET /api/workflow-runbook/latest`
- UI: `/workflow-runbook`

### Lab inventory (read-only)
- `GET /api/lab/inventory`
- UI: `/lab`

### Stage spine endpoints (visibility pages)
- Session Router: `GET /api/session-router/status`, `POST /api/session-router/evaluate`, `GET /api/session-router/latest`
- Workflow Router: `GET /api/workflow-router/status`, `POST /api/workflow-router/route`, `GET /api/workflow-router/latest`
- Strategy Eligibility: `GET /api/strategy-eligibility/status`, `POST /api/strategy-eligibility/check`, `GET /api/strategy-eligibility/latest`
- Trigger Monitoring: `GET /api/trigger-monitoring/status`, `POST /api/trigger-monitoring/evaluate`, `GET /api/trigger-monitoring/latest`
- Execution Planner (preview): `GET /api/execution-planner/status`, `POST /api/execution-planner/plan`, `GET /api/execution-planner/latest`
- Position Monitoring: `GET /api/position-monitoring/status`, `POST /api/position-monitoring/evaluate`, `GET /api/position-monitoring/latest`
- Close Position (review only): `GET /api/close-position/status`, `POST /api/close-position/review`, `GET /api/close-position/latest`
- Post-Trade Evaluation: `GET /api/post-trade-evaluation/status`, `POST /api/post-trade-evaluation/evaluate`, `GET /api/post-trade-evaluation/latest`
- Learning Loop: `GET /api/learning-loop/status`, `POST /api/learning-loop/evaluate`, `GET /api/learning-loop/latest`

### Existing “run” entrypoints (separate from stage spine)
- Command Center:
  - `POST /api/command-center/run`
- Decision workflows:
  - `POST /api/decision-workflows/run-*`
- Market scanner:
  - `POST /api/market-scanner/scan`
- Strategy workflows:
  - `POST /api/strategy-workflows/run`
- Execution workflow (gated; do not enable by default):
  - `/api/execution/*`

## Storage & state (current truth)

- Several stage services store **“latest”** state in-process for visibility (latest snapshot).
- Some workflow systems use **best-effort Postgres persistence** with memory fallback (varies by service).
- **Recommendation lifecycle** and **candidate universe** flows exist independently from the stage spine.

## Safety guarantees (what the platform does not do by default)

- **No broker submission by default**
- **No automatic live trading**
- **No automatic promotion to live trading**
- **No LLM authority required** for the stage spine visibility pages
- Stage 12/9 UIs emphasize preview/review only
- Runbook/dashboard pages are read-only and do not execute stages

## Local run (developer)

Typical dev split:

- Backend: `http://localhost:8900`
- Frontend: `http://localhost:3900`

Primary visibility pages:
- `/workflow-runbook`
- `/lab`
- `/workflow-router`, `/session-router`
- `/strategy-eligibility`, `/trigger-monitoring`, `/execution-planner`
- `/position-monitoring`, `/close-position`
- `/post-trade-evaluation`, `/learning-loop`

## Smoke test

Use the safe smoke script:

```bash
API_BASE_URL="http://localhost:8900" ./scripts/smoke_test_platform.sh
```

The script:
- Runs read-only `GET` checks against runbook + stage status endpoints
- Attempts a best-effort “run” call (prefers orchestrator if present; otherwise command-center) without printing secrets
- Checks common safety flags if present in the response

## Gated items / future hardening

- Persisted Stage 1–14 workflow-run state machine + idempotency keys
- Durable approvals queue for stage handoffs
- Durable scheduler/queue for autonomous progression and retries
- Persistent audit log for governance events
- Explicit scanner → stage spine adapter for seamless handoff

