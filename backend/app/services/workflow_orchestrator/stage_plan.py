from __future__ import annotations

from app.services.agent_runtime.registry import require_agent

# Single source of truth: every key must exist in agent-runtime registry.
# Excludes workflow_orchestrator_agent (orchestrator entrypoint, not a pipeline step).
_ORCHESTRATOR_PIPELINE_AGENT_KEYS: tuple[str, ...] = (
    "account_owner_policy_agent",
    "data_readiness_agent",
    "session_router_agent",
    "market_condition_agent",
    "workflow_router_agent",
    "watchlist_builder_agent",
    "strategy_selection_agent",
    "model_selection_agent",
    "backtest_validation_agent",
    "qlib_research_agent",
    "small_account_feasibility_agent",
    "strategy_eligibility_agent",
    "trigger_monitor_agent",
    "execution_planner_agent",
    "execution_approval_agent",
    "narrative_review_agent",
    "position_monitor_agent",
    "close_review_agent",
    "post_trade_evaluator_agent",
    "learning_loop_agent",
)


def orchestrator_pipeline_agent_count() -> int:
    return len(_ORCHESTRATOR_PIPELINE_AGENT_KEYS)


def default_stage_plan(*, simulated_position: bool = False, simulated_closed_trade: bool = False) -> list[str]:
    """Return the full ordered list of pipeline agents (stages 1–14 + stage-7 extras + optional narrative).

    simulated_position / simulated_closed_trade are kept for API compatibility; the pipeline always
    includes position → close → post-trade → learning (no agents are omitted).
    """
    _ = simulated_position
    _ = simulated_closed_trade
    plan = list(_ORCHESTRATOR_PIPELINE_AGENT_KEYS)
    for key in plan:
        if require_agent(key) is None:
            raise RuntimeError(f"Orchestrator stage plan references unknown agent_key={key!r} (not in agent-runtime registry).")
    return plan
