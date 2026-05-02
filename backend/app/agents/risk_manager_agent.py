from typing import Any

from app.agents.base import AgentRunResult
from app.tools.risk_tools import review_signals_for_paper_only


AGENT_NAME = "Risk Manager Agent"


def run_risk_manager_agent(input_payload: dict[str, Any]) -> AgentRunResult:
    signals = input_payload.get("detected_signals") or []
    review = review_signals_for_paper_only(
        signals,
        account_size=input_payload.get("account_size"),
        max_risk_per_trade=input_payload.get("max_risk_per_trade"),
    )
    passed_count = len([item for item in review["reviews"] if item.get("passed")])
    warnings = ["Live trading remains disabled. Any suggested paper trade requires human approval."]
    return AgentRunResult(
        agent_name=AGENT_NAME,
        status="completed",
        summary=f"Risk reviewed {len(signals)} signal(s); {passed_count} passed paper-only checks.",
        confidence=0.78 if signals else 0.5,
        warnings=warnings,
        errors=[],
        metadata=review,
        data_source=review.get("data_source", "placeholder"),
    )
