from typing import Any

from app.agents.base import AgentRunResult
from app.tools.cost_tools import estimate_llm_cost


AGENT_NAME = "Cost Controller Agent"


def run_cost_controller_agent(input_payload: dict[str, Any]) -> AgentRunResult:
    symbols = input_payload.get("symbols") or []
    estimated_tokens = 1600 + (len(symbols) * 250)
    estimate = estimate_llm_cost(
        model_name=input_payload.get("model_name", "gpt-4o-mini"),
        estimated_tokens=estimated_tokens,
        provider="litellm",
    )
    return AgentRunResult(
        agent_name=AGENT_NAME,
        status="completed",
        summary=f"Estimated placeholder LLM cost at ${estimate['estimated_cost']}.",
        confidence=0.6,
        warnings=["LiteLLM real usage logs are not wired yet; cost estimate is placeholder."],
        errors=[],
        metadata={"cost_estimate": estimate},
        data_source="placeholder",
    )
