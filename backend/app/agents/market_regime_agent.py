from typing import Any

from app.agents.base import AgentRunResult
from app.services.market_regime_service import build_market_regime
from app.tools.market_data_tools import get_safe_market_snapshots, summarize_market_inputs


AGENT_NAME = "Market Regime Agent"


def run_market_regime_agent(input_payload: dict[str, Any]) -> AgentRunResult:
    symbols = input_payload.get("symbols") or ["SPY", "QQQ"]
    requested_source = input_payload.get("data_source", "auto")
    market_data = get_safe_market_snapshots(symbols, source=requested_source)
    regime = build_market_regime()
    summary = f"{regime.regime_state} regime with {round(regime.confidence * 100)}% confidence."
    warnings = list(market_data.get("warnings", []))
    if market_data.get("data_source") != "source_backed":
        warnings.append("Market regime service is currently prototype and should be treated as research context.")
    return AgentRunResult(
        agent_name=AGENT_NAME,
        status="completed",
        summary=summary,
        confidence=regime.confidence,
        warnings=warnings,
        errors=[],
        metadata={
            "regime": regime.model_dump(),
            "market_inputs": summarize_market_inputs(market_data["snapshots"]),
        },
        data_source="source_backed" if market_data.get("data_source") == "source_backed" else "placeholder",
    )
