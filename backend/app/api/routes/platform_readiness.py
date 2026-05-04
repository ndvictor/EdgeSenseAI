"""Platform readiness endpoint for operational visibility."""

import os
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.db.session import check_database_health
from app.services.platform_persistence_status_service import get_database_health_check

router = APIRouter()


class ReadinessCheck(BaseModel):
    key: str
    label: str
    status: Literal["pass", "warn", "fail"]
    message: str
    required_for: str


class PlatformReadinessResponse(BaseModel):
    status: Literal["ready", "partial", "not_ready"]
    checks: list[ReadinessCheck]
    blockers: list[str]
    warnings: list[str]
    generated_at: str


def _check_database_url() -> ReadinessCheck:
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        return ReadinessCheck(
            key="database_url",
            label="DATABASE_URL configured",
            status="pass",
            message="Database URL is configured",
            required_for="persistence",
        )
    return ReadinessCheck(
        key="database_url",
        label="DATABASE_URL configured",
        status="warn",
        message="DATABASE_URL not set - using in-memory fallback",
        required_for="persistence",
    )


def _check_postgres_connection() -> ReadinessCheck:
    health = check_database_health()
    if health.get("connected"):
        return ReadinessCheck(
            key="postgres_connection",
            label="Postgres connection",
            status="pass",
            message="Connected to Postgres",
            required_for="persistence",
        )
    return ReadinessCheck(
        key="postgres_connection",
        label="Postgres connection",
        status="warn",
        message=health.get("message", "Postgres not available - using in-memory fallback"),
        required_for="persistence",
    )


def _check_persistence_tables() -> ReadinessCheck:
    """Check if key persistence tables exist."""
    health = get_database_health_check()
    if health.get("connected") and health.get("core_tables_complete") and health.get("workflow_durability_tables_complete"):
        return ReadinessCheck(
            key="persistence_tables",
            label="Persistence tables exist",
            status="pass",
            message="Core and workflow durability tables exist",
            required_for="persistence",
        )
    if not health.get("connected"):
        return ReadinessCheck(
            key="persistence_tables",
            label="Persistence tables exist",
            status="warn",
            message="Cannot verify tables - Postgres not connected",
            required_for="persistence",
        )
    missing_workflow = health.get("workflow_durability_tables", {}).get("missing", [])
    missing_message = f"Missing workflow durability tables: {', '.join(missing_workflow[:5])}" if missing_workflow else "Some persistence tables may be missing - run migrations"
    return ReadinessCheck(
        key="persistence_tables",
        label="Persistence tables exist",
        status="warn",
        message=missing_message,
        required_for="persistence",
    )


def _check_pgvector() -> ReadinessCheck:
    health = check_database_health()
    pgvector_status = health.get("pgvector_status", "unknown")
    if pgvector_status == "available":
        return ReadinessCheck(
            key="pgvector",
            label="pgvector extension",
            status="pass",
            message="pgvector is available",
            required_for="vector_memory",
        )
    if not health.get("connected"):
        return ReadinessCheck(
            key="pgvector",
            label="pgvector extension",
            status="warn",
            message="Cannot verify pgvector - Postgres not connected",
            required_for="vector_memory",
        )
    return ReadinessCheck(
        key="pgvector",
        label="pgvector extension",
        status="warn",
        message=f"pgvector status: {pgvector_status}",
        required_for="vector_memory",
    )


def _check_redis() -> ReadinessCheck:
    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        return ReadinessCheck(
            key="redis",
            label="Redis configured",
            status="pass",
            message="Redis URL is configured",
            required_for="caching",
        )
    return ReadinessCheck(
        key="redis",
        label="Redis configured",
        status="warn",
        message="REDIS_URL not set - caching disabled",
        required_for="caching",
    )


def _check_market_data_provider() -> ReadinessCheck:
    provider = os.environ.get("MARKET_DATA_PROVIDER", "yfinance").lower()
    preferred = ["alpaca", "polygon"]
    if provider in preferred:
        return ReadinessCheck(
            key="market_data_provider",
            label="Market data provider",
            status="pass",
            message=f"Using preferred provider: {provider}",
            required_for="market_data",
        )
    if provider == "yfinance":
        return ReadinessCheck(
            key="market_data_provider",
            label="Market data provider",
            status="warn",
            message="Using yfinance (fallback) - consider Alpaca or Polygon for production",
            required_for="market_data",
        )
    return ReadinessCheck(
        key="market_data_provider",
        label="Market data provider",
        status="pass",
        message=f"Provider: {provider}",
        required_for="market_data",
    )


def _check_langsmith() -> ReadinessCheck:
    tracing = os.environ.get("LANGSMITH_TRACING", "").lower() in ("true", "1", "yes")
    api_key = bool(os.environ.get("LANGSMITH_API_KEY"))
    project = bool(os.environ.get("LANGSMITH_PROJECT"))

    if tracing and api_key and project:
        return ReadinessCheck(
            key="langsmith",
            label="LangSmith tracing",
            status="pass",
            message="LangSmith is configured for tracing",
            required_for="observability",
        )
    if not tracing:
        return ReadinessCheck(
            key="langsmith",
            label="LangSmith tracing",
            status="warn",
            message="LANGSMITH_TRACING not enabled",
            required_for="observability",
        )
    missing = []
    if not api_key:
        missing.append("LANGSMITH_API_KEY")
    if not project:
        missing.append("LANGSMITH_PROJECT")
    return ReadinessCheck(
        key="langsmith",
        label="LangSmith tracing",
        status="warn",
        message=f"Missing: {', '.join(missing)}",
        required_for="observability",
    )


def _check_llm_gateway_safety() -> ReadinessCheck:
    paid_calls = os.environ.get("LLM_PAID_CALLS_ENABLED", "").lower() in ("true", "1", "yes")
    if paid_calls:
        return ReadinessCheck(
            key="llm_gateway_safety",
            label="LLM Gateway safety",
            status="fail",
            message="LLM paid calls are enabled - safety risk",
            required_for="safety",
        )
    return ReadinessCheck(
        key="llm_gateway_safety",
        label="LLM Gateway safety",
        status="pass",
        message="Paid LLM calls are disabled by default",
        required_for="safety",
    )


def _check_live_trading() -> ReadinessCheck:
    live_enabled = os.environ.get("LIVE_TRADING_ENABLED", "").lower() in ("true", "1", "yes")
    if live_enabled:
        return ReadinessCheck(
            key="live_trading",
            label="Live trading",
            status="fail",
            message="LIVE_TRADING_ENABLED is true - must remain disabled",
            required_for="safety",
        )
    return ReadinessCheck(
        key="live_trading",
        label="Live trading",
        status="pass",
        message="Live trading is disabled",
        required_for="safety",
    )


def _check_human_approval() -> ReadinessCheck:
    approval_required = os.environ.get("REQUIRE_HUMAN_APPROVAL", "true").lower() in ("true", "1", "yes")
    if approval_required:
        return ReadinessCheck(
            key="human_approval",
            label="Human approval required",
            status="pass",
            message="Human approval is required for trades",
            required_for="safety",
        )
    return ReadinessCheck(
        key="human_approval",
        label="Human approval required",
        status="fail",
        message="REQUIRE_HUMAN_APPROVAL is false - safety risk",
        required_for="safety",
    )


def _check_candidate_strategies() -> ReadinessCheck:
    """Verify candidate strategies are marked as research only."""
    from app.strategies.registry import list_candidate_strategies

    candidates = list_candidate_strategies()
    if not candidates:
        return ReadinessCheck(
            key="candidate_strategies",
            label="Candidate strategies",
            status="pass",
            message="No candidate strategies defined",
            required_for="research",
        )

    # Check all candidates are properly marked
    improperly_marked = []
    for s in candidates:
        if s.live_trading_supported:
            improperly_marked.append(f"{s.strategy_key}: live_trading_supported=true")
        if s.status != "candidate":
            improperly_marked.append(f"{s.strategy_key}: status={s.status}")

    if improperly_marked:
        return ReadinessCheck(
            key="candidate_strategies",
            label="Candidate strategies",
            status="fail",
            message=f"Improperly configured: {', '.join(improperly_marked[:3])}",
            required_for="safety",
        )

    return ReadinessCheck(
        key="candidate_strategies",
        label="Candidate strategies",
        status="pass",
        message=f"{len(candidates)} candidate strategies properly marked as research only",
        required_for="research",
    )


@router.get("/platform-readiness", response_model=PlatformReadinessResponse)
def get_platform_readiness():
    """Get platform readiness checklist for persistence and monitoring."""
    checks = [
        _check_database_url(),
        _check_postgres_connection(),
        _check_persistence_tables(),
        _check_pgvector(),
        _check_redis(),
        _check_market_data_provider(),
        _check_langsmith(),
        _check_llm_gateway_safety(),
        _check_live_trading(),
        _check_human_approval(),
        _check_candidate_strategies(),
    ]

    blockers = [c.message for c in checks if c.status == "fail"]
    warnings = [c.message for c in checks if c.status == "warn"]

    # Determine overall status
    if blockers:
        status: Literal["ready", "partial", "not_ready"] = "not_ready"
    elif warnings:
        status = "partial"
    else:
        status = "ready"

    return PlatformReadinessResponse(
        status=status,
        checks=checks,
        blockers=blockers,
        warnings=warnings,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
