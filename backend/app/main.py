from __future__ import annotations

import logging
import time
from typing import Final

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.final_readiness import router as final_readiness_router
from app.api.routes.market_scanner import router as market_scanner_router
from app.api.routes.platform_readiness import router as platform_readiness_router
from app.api.routes.promotion_center import router as promotion_center_router
from app.api.routes.worker_status import router as worker_status_router
from app.api.routes.workflow_orchestrator import router as workflow_orchestrator_router
from app.core.settings import settings
from app.metrics import REQUEST_COUNT, REQUEST_LATENCY, metrics_response
from app.services.health_service import get_health_snapshot
from app.services.market_condition_scanner_service import MarketScannerRequest, MarketScannerResponse, run_market_condition_scan

logger = logging.getLogger(__name__)

LEGACY_DISABLED_REASON: Final[str] = "legacy_runtime_disabled_real_data_only"
_ALLOWED_PRODUCTION_ROUTES: Final[set[tuple[str, str]]] = {
    ("GET", "/health"),
    ("GET", "/api/platform-readiness/status"),
    ("GET", "/api/final-readiness/status"),
    ("POST", "/api/workflow-orchestrator/run"),
    ("GET", "/api/worker-status/latest"),
    ("POST", "/api/scanner/run"),
    ("GET", "/api/promotion/strategies/status"),
    ("GET", "/api/promotion/models/status"),
}


def _production_api_quarantine_enabled() -> bool:
    return (settings.app_env or settings.environment or "").lower().strip() in {"prod", "production"} or (
        settings.environment or ""
    ).lower().strip() in {"prod", "production"}


def _disabled_legacy_response() -> JSONResponse:
    return JSONResponse(
        status_code=410,
        content={
            "status": "disabled",
            "reason": LEGACY_DISABLED_REASON,
            "items": [],
            "symbol": None,
        },
    )


def _is_production_allowed(method: str, path: str) -> bool:
    if method.upper() == "OPTIONS":
        return True
    return (method.upper(), path.rstrip("/") or "/") in _ALLOWED_PRODUCTION_ROUTES


app = FastAPI(
    title="EdgeSenseAI Backend",
    version="0.8.2",
    docs_url=None if _production_api_quarantine_enabled() else "/docs",
    redoc_url=None if _production_api_quarantine_enabled() else "/redoc",
    openapi_url=None if _production_api_quarantine_enabled() else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def production_quarantine_and_metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    path = request.url.path.rstrip("/") or "/"
    method = request.method.upper()
    status_code = 500
    try:
        if _production_api_quarantine_enabled() and not _is_production_allowed(method, path):
            response = _disabled_legacy_response()
            status_code = response.status_code
            return response
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception:
        logger.exception("Unhandled error during request processing")
        raise
    finally:
        duration = time.perf_counter() - start
        route = request.scope.get("route")
        endpoint = getattr(route, "path", None) or path
        REQUEST_LATENCY.labels(method, endpoint).observe(duration)
        REQUEST_COUNT.labels(method, endpoint, str(status_code)).inc()


app.include_router(platform_readiness_router, prefix="/api")
app.include_router(final_readiness_router, prefix="/api")
app.include_router(workflow_orchestrator_router, prefix="/api")
app.include_router(worker_status_router, prefix="/api")
app.include_router(promotion_center_router, prefix="/api")

# Keep the legacy scanner router mounted for non-production inspection, but production
# allowlist exposes only POST /api/scanner/run below.
app.include_router(market_scanner_router, prefix="/api")


@app.get("/health")
def health():
    return get_health_snapshot()


@app.get("/metrics")
def metrics():
    return metrics_response()


@app.post("/api/scanner/run", response_model=MarketScannerResponse)
def post_scanner_run(request: MarketScannerRequest):
    """Production scanner entrypoint. Explicit request only; no scheduled/default symbols."""
    return run_market_condition_scan(request)


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
def disabled_legacy_runtime_fallback(path: str):
    if _production_api_quarantine_enabled():
        return _disabled_legacy_response()
    return JSONResponse(status_code=404, content={"detail": "Not Found"})
