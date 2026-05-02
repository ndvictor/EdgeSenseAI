from typing import Any

from app.agents.base import AgentRunResult
from app.services.llm_gateway_service import run_llm_gateway_call
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
    llm_gateway = run_llm_gateway_call(
        agent_name=AGENT_NAME,
        workflow_name=input_payload.get("workflow_name", "small_account_edge_radar"),
        task_type="data_quality_summary",
        prompt=f"Summarize paper-only risk review for {len(signals)} signal(s); {passed_count} passed.",
        allow_paid_call=False,
        metadata={"signals_reviewed": len(signals), "passed_count": passed_count},
    )
    return AgentRunResult(
        agent_name=AGENT_NAME,
        status="completed",
        summary=f"Risk reviewed {len(signals)} signal(s); {passed_count} passed paper-only checks.",
        confidence=0.78 if signals else 0.5,
        warnings=warnings,
        errors=[],
        metadata={**review, "llm_gateway": llm_gateway.model_dump()},
        data_source=review.get("data_source", "placeholder"),
    )
