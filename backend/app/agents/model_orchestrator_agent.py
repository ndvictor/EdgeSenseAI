from typing import Any

from app.agents.base import AgentRunResult
from app.services.model_orchestrator_service import ModelRunRequest, run_model_orchestrator


AGENT_NAME = "Model Orchestrator Agent"


def run_model_orchestrator_agent(input_payload: dict[str, Any]) -> AgentRunResult:
    result = run_model_orchestrator(ModelRunRequest(**input_payload))
    runnable_models = [model.key for model in result.plan.models if model.should_run]
    return AgentRunResult(
        agent_name=AGENT_NAME,
        status=result.status,
        summary=f"Planned {len(runnable_models)} runnable model(s): {', '.join(runnable_models) or 'none'}.",
        confidence=0.76 if runnable_models else 0.45,
        warnings=result.warnings,
        errors=[],
        metadata=result.model_dump(),
        data_source=result.data_source,
    )
