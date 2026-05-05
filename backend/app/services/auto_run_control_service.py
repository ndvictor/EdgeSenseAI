from pydantic import BaseModel

from app.core.effective_runtime import effective_bool, effective_float, effective_int
from app.core.runtime_settings_store import load_runtime_settings, save_runtime_settings
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


# In-memory: only auto_run flag (not persisted in runtime_settings.json historically)
_STATE_AUTO_RUN = False


def get_auto_run_state() -> AutoRunControlState:
    return AutoRunControlState(
        auto_run_enabled=_STATE_AUTO_RUN,
        live_trading_enabled=effective_bool("LIVE_TRADING_ENABLED"),
        paper_trading_enabled=effective_bool("PAPER_TRADING_ENABLED"),
        require_human_approval=effective_bool("REQUIRE_HUMAN_APPROVAL"),
        max_daily_agent_runs=effective_int("MAX_DAILY_AGENT_RUNS"),
        max_daily_llm_cost=effective_float("MAX_DAILY_LLM_COST"),
    )


def update_auto_run_state(update: AutoRunControlUpdate) -> AutoRunControlState:
    global _STATE_AUTO_RUN
    current = load_runtime_settings()
    if update.auto_run_enabled is not None:
        _STATE_AUTO_RUN = update.auto_run_enabled
    if update.live_trading_enabled is not None:
        current["LIVE_TRADING_ENABLED"] = bool(update.live_trading_enabled and settings.live_trading_enabled)
    if update.paper_trading_enabled is not None:
        current["PAPER_TRADING_ENABLED"] = update.paper_trading_enabled
    if update.require_human_approval is not None:
        current["REQUIRE_HUMAN_APPROVAL"] = update.require_human_approval or settings.require_human_approval
    if update.max_daily_agent_runs is not None:
        current["MAX_DAILY_AGENT_RUNS"] = max(1, update.max_daily_agent_runs)
    if update.max_daily_llm_cost is not None:
        current["MAX_DAILY_LLM_COST"] = max(0.0, update.max_daily_llm_cost)
    if any(
        v is not None
        for v in (
            update.live_trading_enabled,
            update.paper_trading_enabled,
            update.require_human_approval,
            update.max_daily_agent_runs,
            update.max_daily_llm_cost,
        )
    ):
        save_runtime_settings(current)
    return get_auto_run_state()
