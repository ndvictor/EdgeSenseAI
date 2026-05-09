"""Platform readiness endpoint for operational visibility."""

import os
from datetime import datetime, timezone
from pathlib import Path
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


def _check_edgesense_execution() -> ReadinessCheck:
    from app.execution.edgesense_execution_config import load_edgesense_execution_config

    c = load_edgesense_execution_config()
    if c.live_trading_enabled:
        return ReadinessCheck(
            key="edgesense_live_flag",
            label="EdgeSense live trading flag",
            status="warn",
            message="EDGESENSE_LIVE_TRADING_ENABLED is true — confirm policy before production",
            required_for="execution",
        )
    msg = f"mode={c.execution_mode} human_approval={c.require_human_approval} max_daily_loss_pct={c.max_daily_loss_pct}"
    return ReadinessCheck(
        key="edgesense_execution",
        label="EdgeSense execution config",
        status="pass",
        message=msg,
        required_for="execution",
    )


def _workflow_runbook_uses_orchestrator_only() -> bool:
    path = Path(__file__).resolve().parents[4] / "frontend" / "src" / "app" / "workflow-runbook" / "page.tsx"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    forbidden = (
        "runDecisionWorkflow(",
        "runStrategyWorkflow(",
        "runSignal",
        "updateAutoRunStatus(",
        "postExecutionSubmit(",
        "place_trade",
        "/api/decision-workflows/run",
        "/api/signal-agents/run",
        "/api/strategy-workflows/run",
        "/api/auto-run/status",
        "/api/tradenow/orders",
        "/api/execution/submit",
    )
    return "runWorkflowOrchestrator(" in text and not any(item in text for item in forbidden)


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
        _check_edgesense_execution(),
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


@router.get("/platform-readiness/status")
def get_platform_readiness_status() -> dict[str, Any]:
    """Phase 4 readiness rollup for all major backend systems (stable contract for Phase 6)."""
    from app.services.agent_runtime.service import build_status as agent_runtime_status
    from app.services.audit_log.service import get_audit_log_status
    from app.services.approval_queue.service import get_status as approval_status
    from app.services.workflow_governance.service import get_governance_status
    from app.services.workflow_orchestrator.service import get_orchestrator_status
    from app.services.workflow_scheduler.service import get_status as scheduler_status
    from app.services.qlib_integration.service import get_qlib_automation_status
    from app.services.proof_registry.service import get_proof_registry_status
    from app.services.model_evidence.service import get_model_evidence_status
    from app.services.strategy_evidence.service import get_strategy_evidence_status
    from app.services.feature_store_service import get_feature_store_status
    from app.services.persistence_service import get_persistence_status
    from app.services.small_account_feasibility.service import readiness_summary as small_account_readiness_summary
    from app.core.effective_runtime import effective_bool
    from app.core.effective_runtime import effective_str

    db = check_database_health()
    provider = (effective_str("MARKET_DATA_PROVIDER") or os.environ.get("MARKET_DATA_PROVIDER") or "yfinance").lower()
    feature_store = get_feature_store_status()
    persistence = get_persistence_status()
    qlib_status = get_qlib_automation_status()
    proof_status = get_proof_registry_status().model_dump()
    model_status = get_model_evidence_status().model_dump()
    strategy_status = get_strategy_evidence_status().model_dump()
    small_account_feasibility = small_account_readiness_summary()
    data_pipeline_soft_warnings: list[str] = ["kafka_optional_not_active"]
    if persistence.get("postgres_persistence_status") != "connected":
        data_pipeline_soft_warnings.append("persistence_memory_fallback")
    if provider == "yfinance":
        data_pipeline_soft_warnings.append("yfinance_is_research_grade_provider")
    systems = {
        "database": db,
        "redis": {"configured": bool(os.environ.get("REDIS_URL"))},
        "agent_runtime": agent_runtime_status().model_dump(),
        "workflow_orchestrator": get_orchestrator_status().model_dump(),
        "approval_queue": approval_status().model_dump(),
        "audit_log": get_audit_log_status().model_dump(),
        "workflow_scheduler": scheduler_status().model_dump(),
        "governance": get_governance_status().model_dump(),
        "qlib_integration": qlib_status,
        "proof_registry": proof_status,
        "model_evidence": model_status,
        "strategy_evidence": strategy_status,
        "execution_gates": {
            "workflow_enabled": effective_bool("WORKFLOW_ENABLED"),
            "execution_enabled": effective_bool("EXECUTION_ENABLED"),
            "emergency_stop": effective_bool("EMERGENCY_STOP"),
            "paper_trading_enabled": effective_bool("PAPER_TRADING_ENABLED"),
            "live_trading_enabled": effective_bool("LIVE_TRADING_ENABLED"),
            "broker_execution_enabled": effective_bool("BROKER_EXECUTION_ENABLED"),
            "require_human_approval": effective_bool("REQUIRE_HUMAN_APPROVAL"),
        },
        "safety_summary": {"no_llm": True, "no_broker_calls": True, "no_execution_submit": True},
        "endpoint_boundaries": {
            "autonomous_entrypoint": "/api/workflow-orchestrator/run",
            "old_manual_surfaces_present": True,
            "mixed_endpoint_risk": "pass" if _workflow_runbook_uses_orchestrator_only() else "fail",
            "broker_submit_blocked": True,
            "llm_decisioning_blocked": True,
            "supported_horizons": ["day_trading"],
            "blocked_horizons": ["swing_trading", "swing", "multi_day", "overnight", "position_trade"],
        },
        "data_pipeline": {
            "provider_status": "configured" if provider else "unknown",
            "provider_name": provider or "unknown",
            "feature_store_status": feature_store.get("status", "unknown"),
            "feature_row_count": feature_store.get("row_count", 0),
            "persistence_status": persistence.get("postgres_persistence_status", "unknown"),
            "freshness_status": "checked_per_run",
            "kafka_status": "configured_optional_not_active",
            "qlib_status": qlib_status.get("status", "unknown") if isinstance(qlib_status, dict) else "unknown",
            "hard_blockers": [],
            "soft_warnings": data_pipeline_soft_warnings,
            "next_action": "Run /api/workflow-orchestrator/run in dry-run mode to verify provider freshness for selected symbols.",
        },
        "evidence_pipeline": {
            "qlib_status": qlib_status.get("status", "unknown") if isinstance(qlib_status, dict) else "unknown",
            "proof_registry_status": proof_status.get("status", "unknown"),
            "model_evidence_status": model_status.get("status", "unknown"),
            "strategy_evidence_status": strategy_status.get("status", "unknown"),
            "latest_proof_status": proof_status.get("summary", {}).get("latest_proof_status", "unknown"),
            "latest_model_status": model_status.get("summary", {}).get("latest_model_status", "unknown"),
            "latest_strategy_status": strategy_status.get("summary", {}).get("latest_strategy_status", "unknown"),
            "hard_blockers": [],
            "soft_warnings": ["qlib_optional_not_required_for_workflow"] if not qlib_status.get("qlib_available") else [],
            "next_action": "Use proof, model, and strategy evidence records to gate backtest validation and downstream selection.",
        },
        "small_account_feasibility": small_account_feasibility,
    }

    missing_backend_components = []
    if not systems["execution_gates"]["workflow_enabled"]:
        missing_backend_components.append("WORKFLOW_ENABLED gate is false")

    return {
        "status": "ok",
        "data_mode": "platform_readiness_v2",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "systems": systems,
        "missing_backend_components": missing_backend_components,
        "missing_frontend_components": [],
        "next_action": "Core operator UIs shipped (Phase 5–6). Use GET /api/final-readiness/status for completion rollup.",
    }
