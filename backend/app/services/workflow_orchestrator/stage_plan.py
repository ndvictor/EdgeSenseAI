from __future__ import annotations


def default_stage_plan(*, simulated_position: bool, simulated_closed_trade: bool) -> list[str]:
    plan = [
        "account_owner_policy_agent",
        "data_readiness_agent",
        "session_router_agent",
        "market_condition_agent",
        "workflow_router_agent",
        "watchlist_builder_agent",
        "strategy_selection_agent",
        "model_selection_agent",
        "backtest_validation_agent",
        "strategy_eligibility_agent",
        "trigger_monitor_agent",
        "execution_planner_agent",
        "execution_approval_agent",
    ]
    if simulated_position:
        plan.extend(["position_monitor_agent", "close_review_agent"])
    if simulated_closed_trade:
        plan.extend(["post_trade_evaluator_agent", "learning_loop_agent"])
    return plan

