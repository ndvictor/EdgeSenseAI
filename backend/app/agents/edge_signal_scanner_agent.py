from typing import Any

from app.agents.base import AgentRunResult
from app.tools.market_data_tools import get_safe_market_snapshots, summarize_market_inputs


AGENT_NAME = "Edge Signal Scanner Agent"


def _build_watch_signal(snapshot: dict[str, Any], horizon: str) -> dict[str, Any] | None:
    price = snapshot.get("price")
    if price is None:
        return None
    change_percent = float(snapshot.get("change_percent") or 0)
    volume = float(snapshot.get("volume") or 0)
    score = 50 + min(max(change_percent * 5, -15), 20)
    if volume > 0:
        score += 8
    confidence = round(max(0.35, min(0.82, score / 100)), 2)
    if confidence < 0.55:
        return None
    return {
        "symbol": snapshot.get("symbol"),
        "horizon": horizon,
        "signal_type": "watch_setup",
        "current_price": round(float(price), 4),
        "entry_price": round(float(price), 4),
        "stop_loss": round(float(price) * 0.97, 4),
        "target_price": round(float(price) * 1.06, 4),
        "confidence": confidence,
        "score": round(score, 2),
        "reason": "Deterministic first-pass scanner using source-backed snapshot fields when available.",
        "data_source": snapshot.get("data_source", "placeholder"),
    }


def run_edge_signal_scanner_agent(input_payload: dict[str, Any]) -> AgentRunResult:
    symbols = input_payload.get("symbols") or []
    horizon = input_payload.get("horizon", "swing")
    requested_source = input_payload.get("data_source", "auto")
    market_data = get_safe_market_snapshots(symbols, source=requested_source)
    signals = [
        signal
        for signal in (_build_watch_signal(snapshot, horizon) for snapshot in market_data["snapshots"])
        if signal is not None
    ]
    data_source = market_data.get("data_source", "placeholder")
    warnings = list(market_data.get("warnings", []))
    if not signals:
        warnings.append("No watch setups passed deterministic first-pass scanner thresholds.")
    return AgentRunResult(
        agent_name=AGENT_NAME,
        status="completed",
        summary=f"Detected {len(signals)} research watch setup(s).",
        confidence=round(max([signal["confidence"] for signal in signals], default=0.4), 2),
        warnings=warnings,
        errors=[],
        metadata={
            "detected_signals": signals,
            "market_inputs": summarize_market_inputs(market_data["snapshots"]),
        },
        data_source=data_source,
    )
