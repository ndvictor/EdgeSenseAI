"""Day Trading v1 public route contract registry (documentation + GET /contracts/routes)."""

from __future__ import annotations

from typing import Any, TypedDict


class DayTradingV1RouteContract(TypedDict):
    method: str
    path: str
    legacy_sources: str
    description: str


DAYTRADING_V1_ROUTE_CONTRACTS: list[DayTradingV1RouteContract] = [
    {
        "method": "GET",
        "path": "/api/v1/daytrading/status",
        "legacy_sources": "GET /health, GET /api/platform-readiness/status, GET /api/final-readiness/status",
        "description": "Aggregated liveness, platform readiness, and final-readiness rollup for the day-trading operator surface.",
    },
    {
        "method": "POST",
        "path": "/api/v1/daytrading/scanner/run",
        "legacy_sources": "POST /api/scanner/run",
        "description": "Manual real-provider scanner pass; persists candidates via worker output store (same service path as legacy).",
    },
    {
        "method": "GET",
        "path": "/api/v1/daytrading/scanner/latest",
        "legacy_sources": "GET /api/worker-status/latest (scanner-focused projection)",
        "description": "Latest scanner worker snapshot and scanner-oriented diagnostics fields from worker output summary.",
    },
    {
        "method": "GET",
        "path": "/api/v1/daytrading/workers/latest",
        "legacy_sources": "GET /api/worker-status/latest",
        "description": "Full latest worker output summary (scanner, ingestion, feature workers and counts).",
    },
    {
        "method": "POST",
        "path": "/api/v1/daytrading/workflow/run",
        "legacy_sources": "POST /api/workflow-orchestrator/run",
        "description": "Runs the stock day-trading orchestrator workflow (thin wrapper around orchestrator service).",
    },
    {
        "method": "GET",
        "path": "/api/v1/daytrading/workflow/latest",
        "legacy_sources": "GET /api/workflow-orchestrator/latest",
        "description": "Latest persisted orchestrator run payload (service-backed; no HTTP self-call).",
    },
    {
        "method": "GET",
        "path": "/api/v1/daytrading/recommendation/latest",
        "legacy_sources": "Projection from latest orchestrator run (legacy: POST /api/workflow-orchestrator/run response)",
        "description": "Alpha / recommendation fields from the latest orchestrator run.",
    },
    {
        "method": "GET",
        "path": "/api/v1/daytrading/evidence/strategies",
        "legacy_sources": "GET /api/promotion/strategies/status",
        "description": "Promotion readiness for strategies (read-only).",
    },
    {
        "method": "GET",
        "path": "/api/v1/daytrading/evidence/models",
        "legacy_sources": "GET /api/promotion/models/status",
        "description": "Promotion readiness for models (read-only).",
    },
    {
        "method": "GET",
        "path": "/api/v1/daytrading/risk/status",
        "legacy_sources": "Projection from latest orchestrator run (risk / small-account fields)",
        "description": "Risk and small-account outputs from the latest orchestrator run.",
    },
    {
        "method": "GET",
        "path": "/api/v1/daytrading/execution-boundary",
        "legacy_sources": "GET /api/platform-readiness/status + latest orchestrator run safety fields",
        "description": "Execution gates from platform readiness plus broker/submit/approval fields from latest workflow run.",
    },
    {
        "method": "GET",
        "path": "/api/v1/daytrading/contracts/routes",
        "legacy_sources": "n/a (registry)",
        "description": "Machine-readable list of v1 day-trading routes and their legacy mappings.",
    },
]


def contracts_routes_payload() -> dict[str, Any]:
    return {
        "status": "ok",
        "data_mode": "daytrading_v1_route_contracts",
        "routes": list(DAYTRADING_V1_ROUTE_CONTRACTS),
    }
