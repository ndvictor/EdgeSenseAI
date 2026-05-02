from typing import Any

from app.agents.base import AgentRunResult


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
    return AgentRunResult(
        agent_name=AGENT_NAME,
        status="completed",
        summary=f"Prepared {len(watchlist)} paper-review candidate(s); live trading disabled.",
        confidence=0.72 if watchlist else 0.55,
        warnings=["Portfolio manager is deterministic first-pass orchestration, not execution logic."],
        errors=[],
        metadata={"decision": decision},
        data_source="source_backed" if any(signal.get("data_source") == "source_backed" for signal in watchlist) else "placeholder",
    )
