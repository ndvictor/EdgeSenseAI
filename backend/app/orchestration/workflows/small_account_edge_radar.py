from datetime import datetime
from time import perf_counter
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.agents.base import AgentRunResult, AgentTraceEvent
from app.agents.cost_controller_agent import run_cost_controller_agent
from app.agents.edge_signal_scanner_agent import run_edge_signal_scanner_agent
from app.agents.market_regime_agent import run_market_regime_agent
from app.agents.portfolio_manager_agent import run_portfolio_manager_agent
from app.agents.risk_manager_agent import run_risk_manager_agent

try:
    from langgraph.graph import StateGraph
except Exception:  # pragma: no cover - optional until dependencies are installed
    StateGraph = None  # type: ignore[assignment]


WORKFLOW_NAME = "small_account_edge_radar"


class SmallAccountEdgeRadarInput(BaseModel):
    symbols: list[str] = Field(default_factory=lambda: ["AMD", "NVDA", "AAPL", "MSFT", "BTC-USD"])
    asset_classes: list[str] | None = None
    horizon: str = "swing"
    account_size: float | None = None
    max_risk_per_trade: float | None = None
    strategy_preference: str | None = None
    data_source: str = "auto"


class SmallAccountEdgeRadarOutput(BaseModel):
    run_id: str
    workflow_name: str
    status: str
    data_source: str
    message: str
    detected_signals: list[dict[str, Any]]
    regime_context: dict[str, Any]
    risk_review: dict[str, Any]
    portfolio_manager_decision: dict[str, Any]
    approval_required: bool
    paper_trade_allowed: bool
    live_trading_allowed: bool
    cost_estimate: dict[str, Any]
    agent_trace: list[AgentTraceEvent]
    warnings: list[str]
    errors: list[str]
    started_at: datetime
    completed_at: datetime
    duration_ms: float


def build_langgraph_definition() -> dict[str, Any]:
    return {
        "available": StateGraph is not None,
        "workflow_name": WORKFLOW_NAME,
        "nodes": [
            "market_regime_agent",
            "edge_signal_scanner_agent",
            "risk_manager_agent",
            "portfolio_manager_agent",
            "cost_controller_agent",
        ],
        "edges": [
            ("market_regime_agent", "edge_signal_scanner_agent"),
            ("edge_signal_scanner_agent", "risk_manager_agent"),
            ("risk_manager_agent", "portfolio_manager_agent"),
            ("portfolio_manager_agent", "cost_controller_agent"),
        ],
        "status": "compatible_wrapper_ready_for_graph_compile",
    }


def _elapsed_ms(start: float) -> float:
    return round((perf_counter() - start) * 1000, 2)


def _trace_from_result(
    result: AgentRunResult,
    run_id: str,
    started_at: datetime,
    completed_at: datetime,
    duration_ms: float,
    input_summary: str,
) -> AgentTraceEvent:
    return AgentTraceEvent(
        run_id=run_id,
        workflow_name=WORKFLOW_NAME,
        agent_name=result.agent_name,
        status=result.status,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=duration_ms,
        confidence=result.confidence,
        input_summary=input_summary,
        output_summary=result.summary,
        warnings=result.warnings,
        errors=result.errors,
        metadata=result.metadata,
        data_source=result.data_source,
    )


def _run_agent(agent_fn, payload: dict[str, Any], run_id: str, input_summary: str) -> tuple[AgentRunResult, AgentTraceEvent]:
    started_at = datetime.utcnow()
    timer = perf_counter()
    result = agent_fn(payload)
    completed_at = datetime.utcnow()
    duration_ms = _elapsed_ms(timer)
    result.run_id = run_id
    result.workflow_name = WORKFLOW_NAME
    result.started_at = started_at
    result.completed_at = completed_at
    result.duration_ms = duration_ms
    result.input_summary = input_summary
    result.output_summary = result.summary
    return result, _trace_from_result(result, run_id, started_at, completed_at, duration_ms, input_summary)


def _merge_data_source(agent_results: list[AgentRunResult]) -> str:
    sources = {result.data_source for result in agent_results}
    if "source_backed" in sources:
        return "source_backed"
    if "demo" in sources:
        return "demo"
    return "placeholder"


def run_small_account_edge_radar(request: SmallAccountEdgeRadarInput) -> SmallAccountEdgeRadarOutput:
    run_id = f"edge-radar-{uuid4().hex[:12]}"
    started_at = datetime.utcnow()
    workflow_timer = perf_counter()
    trace: list[AgentTraceEvent] = []
    agent_results: list[AgentRunResult] = []
    warnings: list[str] = []
    errors: list[str] = []

    base_payload = request.model_dump()

    regime_result, event = _run_agent(
        run_market_regime_agent,
        base_payload,
        run_id,
        input_summary=f"Regime context for {', '.join(request.symbols)}.",
    )
    trace.append(event)
    agent_results.append(regime_result)

    scanner_payload = {**base_payload, "regime_context": regime_result.metadata.get("regime", {})}
    scanner_result, event = _run_agent(
        run_edge_signal_scanner_agent,
        scanner_payload,
        run_id,
        input_summary=f"Scan {len(request.symbols)} symbol(s) for {request.horizon} watch setups.",
    )
    trace.append(event)
    agent_results.append(scanner_result)
    detected_signals = scanner_result.metadata.get("detected_signals", [])

    risk_payload = {**base_payload, "detected_signals": detected_signals}
    risk_result, event = _run_agent(
        run_risk_manager_agent,
        risk_payload,
        run_id,
        input_summary=f"Paper-only risk review for {len(detected_signals)} signal(s).",
    )
    trace.append(event)
    agent_results.append(risk_result)
    risk_review = risk_result.metadata

    portfolio_payload = {
        **base_payload,
        "detected_signals": detected_signals,
        "risk_reviews": risk_review.get("reviews", []),
    }
    portfolio_result, event = _run_agent(
        run_portfolio_manager_agent,
        portfolio_payload,
        run_id,
        input_summary="Convert risk-reviewed signals into paper-review decisions.",
    )
    trace.append(event)
    agent_results.append(portfolio_result)
    portfolio_decision = portfolio_result.metadata.get("decision", {})

    cost_result, event = _run_agent(
        run_cost_controller_agent,
        base_payload,
        run_id,
        input_summary="Estimate placeholder LLM orchestration cost.",
    )
    trace.append(event)
    agent_results.append(cost_result)

    for result in agent_results:
        warnings.extend(result.warnings)
        errors.extend(result.errors)

    completed_at = datetime.utcnow()
    approval_required = bool(portfolio_decision.get("approval_required"))
    paper_trade_allowed = bool(portfolio_decision.get("paper_trade_allowed")) and request.data_source in {"auto", "yfinance", "mock"}
    return SmallAccountEdgeRadarOutput(
        run_id=run_id,
        workflow_name=WORKFLOW_NAME,
        status="completed" if not errors else "completed_with_errors",
        data_source=_merge_data_source(agent_results),
        message="Small Account Edge Radar completed in paper/research mode. Live trading is disabled.",
        detected_signals=detected_signals,
        regime_context=regime_result.metadata.get("regime", {}),
        risk_review=risk_review,
        portfolio_manager_decision=portfolio_decision,
        approval_required=approval_required,
        paper_trade_allowed=paper_trade_allowed,
        live_trading_allowed=False,
        cost_estimate=cost_result.metadata.get("cost_estimate", {}),
        agent_trace=trace,
        warnings=warnings,
        errors=errors,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=_elapsed_ms(workflow_timer),
    )
