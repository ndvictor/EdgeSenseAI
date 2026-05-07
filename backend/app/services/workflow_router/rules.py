from __future__ import annotations

from dataclasses import dataclass

from app.services.workflow_router.models import (
    CheckerOutcome,
    ExecutionState,
    MarketCondition,
    ProofStatus,
    SessionKey,
    StrategyOrResponseStatus,
    UrgencyLevel,
    WorkflowKey,
    WorkflowMode,
)


@dataclass(frozen=True)
class CheckerEval:
    status: CheckerOutcome
    message: str


@dataclass(frozen=True)
class RouteResult:
    selected_workflow: WorkflowKey
    workflow_mode: WorkflowMode
    reason: str
    blocked_stages: list[dict]
    next_action: str


SUPPORTED_WORKFLOWS: list[WorkflowKey] = [
    "baseline_fast_path",
    "adjusted_research_path",
    "paper_only_path",
    "backtest_queue_path",
    "observe_only_path",
    "no_trade_path",
]


def evaluate_session_checker(session: SessionKey, execution: ExecutionState) -> CheckerEval:
    if session == "market_open" and not execution.broker_ready:
        return CheckerEval("warn", "Market is open but broker is not ready; avoid execution path.")
    return CheckerEval("pass", f"Session '{session}' accepted.")


def evaluate_urgency_checker(urgency: UrgencyLevel) -> CheckerEval:
    if urgency in ("high", "critical"):
        return CheckerEval("pass", f"Urgency is {urgency}; fast-path may be appropriate if proven and checks pass.")
    return CheckerEval("pass", f"Urgency is {urgency}.")


def evaluate_proof_status_checker(proof_status: ProofStatus, session: SessionKey) -> CheckerEval:
    if session == "market_open" and proof_status in ("backtest_required", "research_only", "unknown"):
        return CheckerEval("warn", "Market-open window with unproven proof status; avoid baseline execution workflow.")
    if proof_status in ("proven", "paper_passed"):
        return CheckerEval("pass", f"Proof status '{proof_status}' is sufficient for baseline routing gates.")
    return CheckerEval("warn", f"Proof status '{proof_status}' requires additional validation before baseline routing.")


def evaluate_data_quality_checker(data_quality: str) -> CheckerEval:
    if data_quality == "fail":
        return CheckerEval("fail", "Data quality failed; block trading workflows.")
    if data_quality == "warn":
        return CheckerEval("warn", "Data quality warning; prefer research/paper routes.")
    return CheckerEval("pass", "Data quality passed.")


def evaluate_risk_state_checker(risk_budget_available: bool) -> CheckerEval:
    if not risk_budget_available:
        return CheckerEval("fail", "Risk budget not available; block trading workflows.")
    return CheckerEval("pass", "Risk budget available.")


def evaluate_execution_readiness_checker(session: SessionKey, execution: ExecutionState) -> CheckerEval:
    if session == "market_open" and not execution.broker_ready:
        return CheckerEval("warn", "Broker not ready during market open; avoid execution workflows.")
    if not execution.spread_pass or not execution.slippage_pass:
        return CheckerEval("warn", "Execution quality checks not passing (spread/slippage); avoid baseline fast-path.")
    return CheckerEval("pass", "Execution readiness checks passed.")


def route_rules_v1(
    *,
    session: SessionKey,
    market_condition: MarketCondition,
    strategy_status: StrategyOrResponseStatus,
    account_state: dict,
    execution_state: ExecutionState,
) -> RouteResult:
    """
    Deterministic routing logic v1.

    This is intentionally pure (no I/O, no globals) so it can be unit-tested and
    later lifted into a graph orchestrator without changing semantics.
    """
    blocked: list[dict] = []

    # A) Hard no-trade / observe rules (highest priority safety short-circuits)
    if market_condition.data_quality == "fail":
        return RouteResult(
            selected_workflow="no_trade_path",
            workflow_mode="blocked",
            reason="Data quality failed; do not trade.",
            blocked_stages=[],
            next_action="Fix data quality before running workflows.",
        )

    if not account_state["risk_budget_available"]:
        return RouteResult(
            selected_workflow="no_trade_path",
            workflow_mode="blocked",
            reason="Risk budget not available; do not trade.",
            blocked_stages=[],
            next_action="Restore risk budget / limits before running workflows.",
        )

    if not account_state["paper_trading_enabled"] and not account_state["live_trading_enabled"]:
        return RouteResult(
            selected_workflow="observe_only_path",
            workflow_mode="blocked",
            reason="Neither paper nor live trading is enabled; observe only.",
            blocked_stages=[],
            next_action="Enable paper trading to proceed with safe workflow execution.",
        )

    if market_condition.liquidity_state == "poor":
        return RouteResult(
            selected_workflow="observe_only_path",
            workflow_mode="blocked",
            reason="Liquidity is poor; observe only.",
            blocked_stages=[],
            next_action="Wait for improved liquidity conditions or reduce scope to observation.",
        )

    if session == "market_open" and not execution_state.broker_ready:
        return RouteResult(
            selected_workflow="observe_only_path",
            workflow_mode="blocked",
            reason="Broker not ready during market open; observe only.",
            blocked_stages=[],
            next_action="Restore broker readiness before execution workflows.",
        )

    # F) High volatility override
    if market_condition.volatility_state == "extreme":
        if strategy_status.proof_status in ("proven", "paper_passed"):
            chosen: WorkflowKey = "paper_only_path" if account_state["paper_trading_enabled"] else "observe_only_path"
            return RouteResult(
                selected_workflow=chosen,
                workflow_mode="adjusted" if chosen != "observe_only_path" else "blocked",
                reason="Extreme volatility requires reduced confidence and safer workflow route.",
                blocked_stages=[
                    {
                        "stage": "trade_execution",
                        "reason": "Extreme volatility: block live-like execution paths; prefer paper/observe.",
                    }
                ],
                next_action="Run safe paper/observe workflow and reassess volatility before execution.",
            )
        return RouteResult(
            selected_workflow="no_trade_path",
            workflow_mode="blocked",
            reason="Extreme volatility with unproven setup; do not trade.",
            blocked_stages=[],
            next_action="Run research/backtest workflows when volatility normalizes.",
        )

    # B) Market open fast path
    if (
        session == "market_open"
        and market_condition.urgency in ("high", "critical")
        and strategy_status.proof_status in ("proven", "paper_passed")
        and market_condition.data_quality == "pass"
        and account_state["risk_budget_available"] is True
        and execution_state.spread_pass is True
        and execution_state.slippage_pass is True
    ):
        blocked.append(
            {
                "stage": "deep_backtest",
                "reason": "Do not run slow backtest during short market-open trigger window for already proven responses.",
            }
        )
        return RouteResult(
            selected_workflow="baseline_fast_path",
            workflow_mode="baseline",
            reason=(
                "Market is open, opportunity window is short, proof status is sufficient, and checks pass. "
                "Do not rerun full backtest now."
            ),
            blocked_stages=blocked,
            next_action="Proceed with baseline fast-path workflow stages (watchlist/trigger/execution planning).",
        )

    # C) Market open unproven
    if session == "market_open" and strategy_status.proof_status in ("backtest_required", "research_only", "unknown"):
        chosen = "paper_only_path" if account_state["paper_trading_enabled"] else "observe_only_path"
        return RouteResult(
            selected_workflow=chosen,
            workflow_mode="adjusted" if chosen == "paper_only_path" else "blocked",
            reason="Setup is not proven enough for production workflow during market-open window.",
            blocked_stages=[],
            next_action="Run paper-only validation (or observe) instead of baseline execution path.",
        )

    # D) Pre-market
    if session == "pre_market" and strategy_status.proof_status in ("backtest_required", "research_only", "unknown"):
        return RouteResult(
            selected_workflow="backtest_queue_path",
            workflow_mode="adjusted",
            reason="Pre-market has enough time for research/backtest preparation before market open.",
            blocked_stages=[],
            next_action="Queue backtest/research tasks and prepare for market-open validation.",
        )

    if session == "pre_market" and strategy_status.proof_status in ("proven", "paper_passed"):
        return RouteResult(
            selected_workflow="adjusted_research_path",
            workflow_mode="adjusted",
            reason="Pre-market should prepare watchlist and workflow readiness, not execute immediately.",
            blocked_stages=[],
            next_action="Prepare candidates, triggers, and execution readiness for market open.",
        )

    # E) Post-market / after-hours
    return RouteResult(
        selected_workflow="adjusted_research_path",
        workflow_mode="adjusted",
        reason="Post-market and after-hours are for review, backtest, learning loop, and preparation.",
        blocked_stages=[],
        next_action="Run research, review, and preparation workflows.",
    )

from __future__ import annotations

from dataclasses import dataclass

from app.services.workflow_router.models import (
    CheckerOutcome,
    ExecutionState,
    MarketCondition,
    ProofStatus,
    SessionKey,
    StrategyOrResponseStatus,
    UrgencyLevel,
    WorkflowKey,
    WorkflowMode,
)


@dataclass(frozen=True)
class CheckerEval:
    status: CheckerOutcome
    message: str


@dataclass(frozen=True)
class RouteResult:
    selected_workflow: WorkflowKey
    workflow_mode: WorkflowMode
    reason: str
    blocked_stages: list[dict]
    next_action: str


SUPPORTED_WORKFLOWS: list[WorkflowKey] = [
    "baseline_fast_path",
    "adjusted_research_path",
    "paper_only_path",
    "backtest_queue_path",
    "observe_only_path",
    "no_trade_path",
]


def evaluate_session_checker(session: SessionKey, execution: ExecutionState) -> CheckerEval:
    if session == "market_open" and not execution.broker_ready:
        return CheckerEval("warn", "Market is open but broker is not ready; avoid execution path.")
    return CheckerEval("pass", f"Session '{session}' accepted.")


def evaluate_urgency_checker(urgency: UrgencyLevel) -> CheckerEval:
    if urgency in ("high", "critical"):
        return CheckerEval("pass", f"Urgency is {urgency}; fast-path may be appropriate if proven and checks pass.")
    return CheckerEval("pass", f"Urgency is {urgency}.")


def evaluate_proof_status_checker(proof_status: ProofStatus, session: SessionKey) -> CheckerEval:
    if session == "market_open" and proof_status in ("backtest_required", "research_only", "unknown"):
        return CheckerEval("warn", "Market-open window with unproven proof status; avoid baseline execution workflow.")
    if proof_status in ("proven", "paper_passed"):
        return CheckerEval("pass", f"Proof status '{proof_status}' is sufficient for baseline routing gates.")
    return CheckerEval("warn", f"Proof status '{proof_status}' requires additional validation before baseline routing.")


def evaluate_data_quality_checker(data_quality: str) -> CheckerEval:
    if data_quality == "fail":
        return CheckerEval("fail", "Data quality failed; block trading workflows.")
    if data_quality == "warn":
        return CheckerEval("warn", "Data quality warning; prefer research/paper routes.")
    return CheckerEval("pass", "Data quality passed.")


def evaluate_risk_state_checker(risk_budget_available: bool) -> CheckerEval:
    if not risk_budget_available:
        return CheckerEval("fail", "Risk budget not available; block trading workflows.")
    return CheckerEval("pass", "Risk budget available.")


def evaluate_execution_readiness_checker(session: SessionKey, execution: ExecutionState) -> CheckerEval:
    if session == "market_open" and not execution.broker_ready:
        return CheckerEval("warn", "Broker not ready during market open; avoid execution workflows.")
    if not execution.spread_pass or not execution.slippage_pass:
        return CheckerEval("warn", "Execution quality checks not passing (spread/slippage); avoid baseline fast-path.")
    return CheckerEval("pass", "Execution readiness checks passed.")


def route_rules_v1(
    *,
    session: SessionKey,
    market_condition: MarketCondition,
    strategy_status: StrategyOrResponseStatus,
    account_state: dict,
    execution_state: ExecutionState,
) -> RouteResult:
    """
    Deterministic routing logic v1.

    This is intentionally pure (no I/O, no globals) so it can be unit-tested and
    later lifted into a graph orchestrator without changing semantics.
    """
    blocked: list[dict] = []

    # A) Hard no-trade / observe rules (highest priority safety short-circuits)
    if market_condition.data_quality == "fail":
        return RouteResult(
            selected_workflow="no_trade_path",
            workflow_mode="blocked",
            reason="Data quality failed; do not trade.",
            blocked_stages=[],
            next_action="Fix data quality before running workflows.",
        )

    if not account_state["risk_budget_available"]:
        return RouteResult(
            selected_workflow="no_trade_path",
            workflow_mode="blocked",
            reason="Risk budget not available; do not trade.",
            blocked_stages=[],
            next_action="Restore risk budget / limits before running workflows.",
        )

    if not account_state["paper_trading_enabled"] and not account_state["live_trading_enabled"]:
        return RouteResult(
            selected_workflow="observe_only_path",
            workflow_mode="blocked",
            reason="Neither paper nor live trading is enabled; observe only.",
            blocked_stages=[],
            next_action="Enable paper trading to proceed with safe workflow execution.",
        )

    if market_condition.liquidity_state == "poor":
        return RouteResult(
            selected_workflow="observe_only_path",
            workflow_mode="blocked",
            reason="Liquidity is poor; observe only.",
            blocked_stages=[],
            next_action="Wait for improved liquidity conditions or reduce scope to observation.",
        )

    if session == "market_open" and not execution_state.broker_ready:
        return RouteResult(
            selected_workflow="observe_only_path",
            workflow_mode="blocked",
            reason="Broker not ready during market open; observe only.",
            blocked_stages=[],
            next_action="Restore broker readiness before execution workflows.",
        )

    # F) High volatility override
    if market_condition.volatility_state == "extreme":
        if strategy_status.proof_status in ("proven", "paper_passed"):
            chosen: WorkflowKey = "paper_only_path" if account_state["paper_trading_enabled"] else "observe_only_path"
            return RouteResult(
                selected_workflow=chosen,
                workflow_mode="adjusted" if chosen != "observe_only_path" else "blocked",
                reason="Extreme volatility requires reduced confidence and safer workflow route.",
                blocked_stages=[
                    {
                        "stage": "trade_execution",
                        "reason": "Extreme volatility: block live-like execution paths; prefer paper/observe.",
                    }
                ],
                next_action="Run safe paper/observe workflow and reassess volatility before execution.",
            )
        return RouteResult(
            selected_workflow="no_trade_path",
            workflow_mode="blocked",
            reason="Extreme volatility with unproven setup; do not trade.",
            blocked_stages=[],
            next_action="Run research/backtest workflows when volatility normalizes.",
        )

    # B) Market open fast path
    if (
        session == "market_open"
        and market_condition.urgency in ("high", "critical")
        and strategy_status.proof_status in ("proven", "paper_passed")
        and market_condition.data_quality == "pass"
        and account_state["risk_budget_available"] is True
        and execution_state.spread_pass is True
        and execution_state.slippage_pass is True
    ):
        blocked.append(
            {
                "stage": "deep_backtest",
                "reason": "Do not run slow backtest during short market-open trigger window for already proven responses.",
            }
        )
        return RouteResult(
            selected_workflow="baseline_fast_path",
            workflow_mode="baseline",
            reason=(
                "Market is open, opportunity window is short, proof status is sufficient, and checks pass. "
                "Do not rerun full backtest now."
            ),
            blocked_stages=blocked,
            next_action="Proceed with baseline fast-path workflow stages (watchlist/trigger/execution planning).",
        )

    # C) Market open unproven
    if session == "market_open" and strategy_status.proof_status in ("backtest_required", "research_only", "unknown"):
        chosen = "paper_only_path" if account_state["paper_trading_enabled"] else "observe_only_path"
        return RouteResult(
            selected_workflow=chosen,
            workflow_mode="adjusted" if chosen == "paper_only_path" else "blocked",
            reason="Setup is not proven enough for production workflow during market-open window.",
            blocked_stages=[],
            next_action="Run paper-only validation (or observe) instead of baseline execution path.",
        )

    # D) Pre-market
    if session == "pre_market" and strategy_status.proof_status in ("backtest_required", "research_only", "unknown"):
        return RouteResult(
            selected_workflow="backtest_queue_path",
            workflow_mode="adjusted",
            reason="Pre-market has enough time for research/backtest preparation before market open.",
            blocked_stages=[],
            next_action="Queue backtest/research tasks and prepare for market-open validation.",
        )

    if session == "pre_market" and strategy_status.proof_status in ("proven", "paper_passed"):
        return RouteResult(
            selected_workflow="adjusted_research_path",
            workflow_mode="adjusted",
            reason="Pre-market should prepare watchlist and workflow readiness, not execute immediately.",
            blocked_stages=[],
            next_action="Prepare candidates, triggers, and execution readiness for market open.",
        )

    # E) Post-market / after-hours
    return RouteResult(
        selected_workflow="adjusted_research_path",
        workflow_mode="adjusted",
        reason="Post-market and after-hours are for review, backtest, learning loop, and preparation.",
        blocked_stages=[],
        next_action="Run research, review, and preparation workflows.",
    )

