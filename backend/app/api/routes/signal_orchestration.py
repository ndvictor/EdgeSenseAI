from fastapi import APIRouter

from app.services.platform_workflows import SignalAgentRunRequest, SignalAgentRunResponse, run_signal_agents

router = APIRouter()


@router.post("/signal-agents/run", response_model=SignalAgentRunResponse)
def post_signal_run(request: SignalAgentRunRequest):
    return run_signal_agents(request)
