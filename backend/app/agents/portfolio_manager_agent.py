from typing import Any

from app.agents.base import AgentRunResult
from app.services.llm_gateway_service import run_llm_gateway_call


AGENT_NAME = "Portfolio Manager Agent"


def run_portfolio_manager_agent(input_payload: dict[str, Any]) -> AgentRunResult:
    signals = input_payload.get("detected_signals") or []
    risk_reviews = input_payload.get("risk_reviews") or []
    approved_symbols = {review.get("symbol") for review in risk_reviews if review.get("passed")}
    watchlist = [signal for signal in signals if signal.get("symbol") in approved_symbols]
    decision = {
        "action": "paper_watchlist_review" if watchlist else "watch_only",
        "paper_trade_candidates": watchlist,
        "approval_required": bool(watchlist),
        "paper_trade_allowed": bool(watchlist),
        "live_trading_allowed": False,
        "notes": [
            "No live broker APIs are called.",
            "Paper candidates are suggestions only and require human approval.",
        ],
    }
    llm_gateway = run_llm_gateway_call(
        agent_name=AGENT_NAME,
        workflow_name=input_payload.get("workflow_name", "small_account_edge_radar"),
        task_type="portfolio_manager_decision",
        prompt=f"Review paper-only portfolio decision for {len(watchlist)} candidate(s). Live trading disabled.",
        allow_paid_call=False,
        metadata={"candidate_count": len(watchlist), "live_trading_allowed": False},
    )
    return AgentRunResult(
        agent_name=AGENT_NAME,
        status="completed",
        summary=f"Prepared {len(watchlist)} paper-review candidate(s); live trading disabled.",
        confidence=0.72 if watchlist else 0.55,
        warnings=["Portfolio manager is deterministic first-pass orchestration, not execution logic."],
        errors=[],
        metadata={"decision": decision, "llm_gateway": llm_gateway.model_dump()},
        data_source="source_backed" if any(signal.get("data_source") == "source_backed" for signal in watchlist) else "placeholder",
    )
