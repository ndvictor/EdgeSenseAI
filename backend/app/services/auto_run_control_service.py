from pydantic import BaseModel

from app.core.settings import settings


class AutoRunControlState(BaseModel):
    auto_run_enabled: bool = False
    live_trading_enabled: bool = False
    paper_trading_enabled: bool = True
    require_human_approval: bool = True
    max_daily_agent_runs: int
    max_daily_llm_cost: float
    status: str = "configured"
    data_source: str = "source_backed"


class AutoRunControlUpdate(BaseModel):
    auto_run_enabled: bool | None = None
    live_trading_enabled: bool | None = None
    paper_trading_enabled: bool | None = None
    require_human_approval: bool | None = None
    max_daily_agent_runs: int | None = None
    max_daily_llm_cost: float | None = None


_STATE = AutoRunControlState(
    auto_run_enabled=False,
    live_trading_enabled=settings.live_trading_enabled,
    paper_trading_enabled=settings.paper_trading_enabled,
    require_human_approval=settings.require_human_approval,
    max_daily_agent_runs=settings.max_daily_agent_runs,
    max_daily_llm_cost=float(settings.max_daily_llm_cost),
)


def get_auto_run_state() -> AutoRunControlState:
    return _STATE


def update_auto_run_state(update: AutoRunControlUpdate) -> AutoRunControlState:
    global _STATE
    current = _STATE.model_copy()
    if update.auto_run_enabled is not None:
        current.auto_run_enabled = update.auto_run_enabled
    if update.live_trading_enabled is not None:
        current.live_trading_enabled = bool(update.live_trading_enabled and settings.live_trading_enabled)
    if update.paper_trading_enabled is not None:
        current.paper_trading_enabled = update.paper_trading_enabled
    if update.require_human_approval is not None:
        current.require_human_approval = update.require_human_approval or settings.require_human_approval
    if update.max_daily_agent_runs is not None:
        current.max_daily_agent_runs = max(1, update.max_daily_agent_runs)
    if update.max_daily_llm_cost is not None:
        current.max_daily_llm_cost = max(0.0, update.max_daily_llm_cost)
    current.status = "configured"
    _STATE = current
    return _STATE
