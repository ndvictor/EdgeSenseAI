from __future__ import annotations

from app.services.agent_runtime.models import AgentDescriptor


_FORBIDDEN_DEFAULT = [
    "broker_order_submit",
    "live_trade_submit",
    "execution_submit_without_approval",
    "modify_runtime_settings_without_owner",
    "auto_promote_live",
]


def _d(
    *,
    agent_key: str,
    display_name: str,
    role: str,
    stage_number: int | None,
    agent_type: str,
    status: str,
    uses_llm: bool = False,
    allowed_tools: list[str] | None = None,
    forbidden_actions: list[str] | None = None,
    input_schema_name: str | None = None,
    output_schema_name: str | None = None,
    safety_notes: list[str] | None = None,
) -> AgentDescriptor:
    return AgentDescriptor(
        agent_key=agent_key,
        display_name=display_name,
        role=role,
        stage_number=stage_number,
        agent_type=agent_type,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        uses_llm=uses_llm,
        allowed_tools=allowed_tools or [],
        forbidden_actions=forbidden_actions or list(_FORBIDDEN_DEFAULT),
        input_schema_name=input_schema_name,
        output_schema_name=output_schema_name,
        safety_notes=safety_notes or ["Phase 0/1: registry only. No tool execution until Phase 2."],
    )


_AGENTS: dict[str, AgentDescriptor] = {
    "account_owner_policy_agent": _d(
        agent_key="account_owner_policy_agent",
        display_name="Account Owner Policy Agent",
        role="Stage 1 policy/gates",
        stage_number=1,
        agent_type="deterministic_agent",
        status="ready",
    ),
    "data_readiness_agent": _d(
        agent_key="data_readiness_agent",
        display_name="Data Readiness Agent",
        role="Stage 2 data readiness",
        stage_number=2,
        agent_type="deterministic_agent",
        status="ready",
    ),
    "session_router_agent": _d(
        agent_key="session_router_agent",
        display_name="Session Router Agent",
        role="Stage 3 session routing",
        stage_number=3,
        agent_type="deterministic_agent",
        status="ready",
    ),
    "market_condition_agent": _d(
        agent_key="market_condition_agent",
        display_name="Market Condition Agent",
        role="Stage 4 market condition scan",
        stage_number=4,
        agent_type="deterministic_agent",
        status="ready",
    ),
    "workflow_router_agent": _d(
        agent_key="workflow_router_agent",
        display_name="Workflow Router Agent",
        role="Stage 5 workflow routing",
        stage_number=5,
        agent_type="deterministic_agent",
        status="ready",
    ),
    "watchlist_builder_agent": _d(
        agent_key="watchlist_builder_agent",
        display_name="Watchlist Builder Agent",
        role="Stage 6 watchlist building",
        stage_number=6,
        agent_type="deterministic_agent",
        status="ready",
    ),
    "strategy_selection_agent": _d(
        agent_key="strategy_selection_agent",
        display_name="Strategy Selection Agent",
        role="Stage 7 strategy selection",
        stage_number=7,
        agent_type="deterministic_agent",
        status="ready",
    ),
    "model_selection_agent": _d(
        agent_key="model_selection_agent",
        display_name="Model Selection Agent",
        role="Stage 7 model selection",
        stage_number=7,
        agent_type="deterministic_agent",
        status="ready",
    ),
    "small_account_feasibility_agent": _d(
        agent_key="small_account_feasibility_agent",
        display_name="Small Account Feasibility Agent",
        role="Stage 7 small-account feasibility",
        stage_number=7,
        agent_type="deterministic_agent",
        status="ready",
    ),
    "strategy_eligibility_agent": _d(
        agent_key="strategy_eligibility_agent",
        display_name="Strategy Eligibility Agent",
        role="Stage 7 eligibility checks",
        stage_number=7,
        agent_type="deterministic_agent",
        status="ready",
    ),
    "trigger_monitor_agent": _d(
        agent_key="trigger_monitor_agent",
        display_name="Trigger Monitor Agent",
        role="Stage 8 trigger monitoring",
        stage_number=8,
        agent_type="deterministic_agent",
        status="ready",
    ),
    "execution_planner_agent": _d(
        agent_key="execution_planner_agent",
        display_name="Execution Planner Agent",
        role="Stage 9 execution planning",
        stage_number=9,
        agent_type="deterministic_agent",
        status="ready",
    ),
    "execution_approval_agent": _d(
        agent_key="execution_approval_agent",
        display_name="Execution Approval Agent",
        role="Stage 10 approval workflow",
        stage_number=10,
        agent_type="deterministic_agent",
        status="ready",
    ),
    "position_monitor_agent": _d(
        agent_key="position_monitor_agent",
        display_name="Position Monitor Agent",
        role="Stage 11 position monitoring",
        stage_number=11,
        agent_type="deterministic_agent",
        status="ready",
    ),
    "close_review_agent": _d(
        agent_key="close_review_agent",
        display_name="Close Review Agent",
        role="Stage 12 close/reduce review",
        stage_number=12,
        agent_type="deterministic_agent",
        status="ready",
    ),
    "post_trade_evaluator_agent": _d(
        agent_key="post_trade_evaluator_agent",
        display_name="Post-Trade Evaluator Agent",
        role="Stage 13 post-trade evaluation",
        stage_number=13,
        agent_type="deterministic_agent",
        status="ready",
    ),
    "learning_loop_agent": _d(
        agent_key="learning_loop_agent",
        display_name="Learning Loop Agent",
        role="Stage 14 learning loop",
        stage_number=14,
        agent_type="deterministic_agent",
        status="ready",
    ),
    "narrative_review_agent": _d(
        agent_key="narrative_review_agent",
        display_name="Narrative Review Agent",
        role="Optional narrative review (LLM; deferred)",
        stage_number=None,
        agent_type="llm_agent",
        status="ready",
        uses_llm=True,
        safety_notes=["Policy-driven: v1 defaults to skipped (no LLM calls)."],
    ),
    "backtest_validation_agent": _d(
        agent_key="backtest_validation_agent",
        display_name="Backtest Validation Agent",
        role="Stage 7 backtest/proof validation",
        stage_number=7,
        agent_type="deterministic_agent",
        status="ready",
    ),
    "qlib_research_agent": _d(
        agent_key="qlib_research_agent",
        display_name="Qlib Research Agent",
        role="Qlib research/backtest integration (extra)",
        stage_number=7,
        agent_type="deterministic_agent",
        status="ready",
    ),
    "workflow_orchestrator_agent": _d(
        agent_key="workflow_orchestrator_agent",
        display_name="Workflow Orchestrator Agent",
        role="Orchestrate multi-stage workflow (Phase 2+; deferred)",
        stage_number=0,
        agent_type="orchestrator_agent",
        status="ready",
    ),
}


def list_agents() -> list[AgentDescriptor]:
    return list(_AGENTS.values())


def require_agent(agent_key: str) -> AgentDescriptor | None:
    return _AGENTS.get(agent_key)

