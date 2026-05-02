from datetime import datetime
from typing import Any

from fastapi import APIRouter

from app.orchestration.schedulers.edge_scheduler import list_scheduler_jobs
from app.orchestration.workflows.small_account_edge_radar import build_langgraph_definition
from app.services.feature_store_service import get_feature_store_status
from app.services.llm_gateway_service import get_gateway_summary
from app.services.model_orchestrator_service import get_model_registry
from app.services.platform_workflows import get_agent_scorecards

router = APIRouter()


def _now() -> str:
    return datetime.utcnow().isoformat()


@router.get("/ai-ops/summary")
def get_ai_ops_summary() -> dict[str, Any]:
    scorecards = get_agent_scorecards()
    scheduler = list_scheduler_jobs()
    feature_store = get_feature_store_status()
    model_registry = get_model_registry()
    llm_gateway = get_gateway_summary()
    return {
        "data_source": "source_backed",
        "status": "foundation_installed",
        "generated_at": _now(),
        "orchestration": {
            "langgraph": build_langgraph_definition(),
            "deepagents": {"installed_via_requirements": True, "status": "not_wired"},
            "litellm": {"installed_via_requirements": True, "status": "placeholder_cost_estimates_only"},
            "apscheduler": scheduler,
        },
        "data_quality": {"agent": "Data Quality Agent", "status": "configured", "data_source": "source_backed"},
        "feature_store": feature_store,
        "model_orchestrator": {"agent": "Model Orchestrator Agent", "status": "configured", "data_source": "source_backed"},
        "model_registry_summary": {
            "available_model_count": model_registry["available_model_count"],
            "placeholder_model_count": model_registry["placeholder_model_count"],
        },
        "llm_gateway": llm_gateway,
        "agent_scorecards_available": len(scorecards),
        "live_trading_allowed": False,
        "paper_trading_requires_approval": True,
    }


@router.get("/ai-ops/workflows")
def get_ai_ops_workflows() -> dict[str, Any]:
    return {
        "data_source": "placeholder",
        "workflows": [
            {
                "name": "small_account_edge_radar",
                "status": "configured",
                "mode": "paper_research_only",
                "langgraph": build_langgraph_definition(),
                "entrypoint": "POST /api/agents/edge-radar/run",
                "live_trading_allowed": False,
            },
            {
                "name": "signal_agents",
                "status": "preserved_existing",
                "mode": "feature_generation",
                "entrypoint": "POST /api/signal-agents/run",
                "live_trading_allowed": False,
            },
            {
                "name": "feature_store_pipeline",
                "status": "configured",
                "mode": "quality_normalize_feature_store",
                "entrypoint": "POST /api/feature-store/run",
                "live_trading_allowed": False,
            },
            {
                "name": "model_orchestrator",
                "status": "configured",
                "mode": "model_selection_and_research_scoring",
                "entrypoint": "POST /api/model-runs/run",
                "live_trading_allowed": False,
            },
        ],
    }


@router.get("/ai-ops/agents/status")
def get_ai_ops_agents_status() -> dict[str, Any]:
    existing_scorecards = [scorecard.model_dump() for scorecard in get_agent_scorecards()]
    foundation_agents = [
        {"agent_name": "Market Regime Agent", "status": "configured", "data_source": "placeholder"},
        {"agent_name": "Edge Signal Scanner Agent", "status": "configured", "data_source": "placeholder"},
        {"agent_name": "Risk Manager Agent", "status": "configured", "data_source": "source_backed"},
        {"agent_name": "Portfolio Manager Agent", "status": "configured", "data_source": "placeholder"},
        {"agent_name": "Cost Controller Agent", "status": "configured", "data_source": "placeholder"},
        {"agent_name": "Data Quality Agent", "status": "configured", "data_source": "source_backed"},
        {"agent_name": "Model Orchestrator Agent", "status": "configured", "data_source": "source_backed"},
    ]
    return {
        "data_source": "source_backed",
        "existing_scorecards": existing_scorecards,
        "foundation_agents": foundation_agents,
        "feature_store_status": get_feature_store_status(),
        "model_registry_summary": get_model_registry(),
    }


@router.get("/ai-ops/llm-usage")
def get_ai_ops_llm_usage() -> dict[str, Any]:
    return {
        "data_source": "placeholder",
        "status": "placeholder_until_litellm_usage_logs_are_wired",
        "provider": "litellm",
        "total_estimated_cost": 0.0,
        "total_estimated_tokens": 0,
        "models": [],
        "notes": ["LiteLLM is added as a dependency, but real usage logging is not wired in this pass."],
    }


@router.get("/ai-ops/scheduler/jobs")
def get_ai_ops_scheduler_jobs() -> dict[str, Any]:
    return list_scheduler_jobs()


@router.get("/ai-ops/audit-events")
def get_ai_ops_audit_events() -> dict[str, Any]:
    return {
        "data_source": "placeholder",
        "events": [
            {
                "id": "audit-foundation-installed",
                "event_type": "orchestration_foundation",
                "summary": "Agent orchestration foundation configured without live trading execution.",
                "created_at": _now(),
                "severity": "info",
            }
        ],
        "notes": ["Persistent audit storage is not wired in this pass."],
    }
