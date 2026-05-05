"""Settings API Routes - Runtime configuration management.

Allows reading and updating runtime settings via the UI without restarting.
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.runtime_settings_store import load_runtime_settings, save_runtime_settings
from app.core.settings import settings

router = APIRouter()


class TradingSettings(BaseModel):
    paper_trading_enabled: bool
    live_trading_enabled: bool
    broker_execution_enabled: bool
    require_human_approval: bool
    execution_mode: str
    execution_agent_enabled: bool
    paper_starting_cash: float
    broker_provider: str
    alpaca_paper_trade: bool


class LlmGatewaySettings(BaseModel):
    llm_gateway_enable_paid_tests: bool
    llm_gateway_daily_budget: float
    llm_gateway_default_cheap_model: str
    llm_gateway_default_reasoning_model: str
    llm_gateway_default_fallback_model: str
    embeddings_enable_paid_calls: bool


class MarketDataSettings(BaseModel):
    market_data_provider: str
    market_data_provider_priority: str
    market_data_provider_timeout_seconds: int
    alpaca_market_data_enabled: bool


class NewsSettings(BaseModel):
    news_provider_enabled: bool
    news_provider_primary: str
    news_provider_timeout_seconds: int


class PlatformFeatures(BaseModel):
    langsmith_tracing: bool
    vector_memory_enabled: bool


class RateLimitSettings(BaseModel):
    max_daily_llm_cost: int
    max_daily_agent_runs: int


class RiskSettings(BaseModel):
    max_risk_per_trade_percent: float
    max_daily_loss_percent: float
    max_position_size_percent: float
    min_reward_risk_ratio: float


class SettingsResponse(BaseModel):
    trading: TradingSettings
    risk: RiskSettings
    llm_gateway: LlmGatewaySettings
    market_data: MarketDataSettings
    news: NewsSettings
    platform: PlatformFeatures
    rate_limits: RateLimitSettings


class TradingSettingsUpdate(BaseModel):
    paper_trading_enabled: bool | None = None
    live_trading_enabled: bool | None = None
    broker_execution_enabled: bool | None = None
    require_human_approval: bool | None = None
    execution_mode: str | None = None
    execution_agent_enabled: bool | None = None
    paper_starting_cash: float | None = None
    broker_provider: str | None = None
    alpaca_paper_trade: bool | None = None


class LlmGatewaySettingsUpdate(BaseModel):
    llm_gateway_enable_paid_tests: bool | None = None
    llm_gateway_daily_budget: float | None = None
    llm_gateway_default_cheap_model: str | None = None
    llm_gateway_default_reasoning_model: str | None = None
    llm_gateway_default_fallback_model: str | None = None
    embeddings_enable_paid_calls: bool | None = None


class MarketDataSettingsUpdate(BaseModel):
    market_data_provider: str | None = None
    market_data_provider_priority: str | None = None
    market_data_provider_timeout_seconds: int | None = None
    alpaca_market_data_enabled: bool | None = None


class NewsSettingsUpdate(BaseModel):
    news_provider_enabled: bool | None = None
    news_provider_primary: str | None = None
    news_provider_timeout_seconds: int | None = None


class PlatformFeaturesUpdate(BaseModel):
    langsmith_tracing: bool | None = None
    vector_memory_enabled: bool | None = None


class RateLimitSettingsUpdate(BaseModel):
    max_daily_llm_cost: int | None = None
    max_daily_agent_runs: int | None = None


class RiskSettingsUpdate(BaseModel):
    max_risk_per_trade_percent: float | None = None
    max_daily_loss_percent: float | None = None
    max_position_size_percent: float | None = None
    min_reward_risk_ratio: float | None = None


class SettingsUpdateRequest(BaseModel):
    trading: TradingSettingsUpdate | None = None
    risk: RiskSettingsUpdate | None = None
    llm_gateway: LlmGatewaySettingsUpdate | None = None
    market_data: MarketDataSettingsUpdate | None = None
    news: NewsSettingsUpdate | None = None
    platform: PlatformFeaturesUpdate | None = None
    rate_limits: RateLimitSettingsUpdate | None = None


def _get_runtime_value(key: str, default: Any) -> Any:
    """Get value from runtime settings with fallback to env settings."""
    runtime = load_runtime_settings()
    return runtime.get(key, getattr(settings, key.lower(), default))


@router.get("/settings", response_model=SettingsResponse)
def get_settings() -> SettingsResponse:
    """Get current runtime settings.
    
    Returns the active configuration that can be toggled without restart.
    """
    runtime = load_runtime_settings()
    
    # Priority: runtime_settings.json > .env > defaults
    return SettingsResponse(
        trading=TradingSettings(
            paper_trading_enabled=runtime.get("PAPER_TRADING_ENABLED", settings.paper_trading_enabled),
            live_trading_enabled=runtime.get("LIVE_TRADING_ENABLED", settings.live_trading_enabled),
            broker_execution_enabled=runtime.get("BROKER_EXECUTION_ENABLED", settings.broker_execution_enabled),
            require_human_approval=runtime.get("REQUIRE_HUMAN_APPROVAL", settings.require_human_approval),
            execution_mode=runtime.get("EXECUTION_MODE", settings.execution_mode),
            execution_agent_enabled=runtime.get("EXECUTION_AGENT_ENABLED", settings.execution_agent_enabled),
            paper_starting_cash=runtime.get("PAPER_STARTING_CASH", settings.paper_starting_cash),
            broker_provider=runtime.get("BROKER_PROVIDER", settings.broker_provider),
            alpaca_paper_trade=runtime.get("ALPACA_PAPER_TRADE", settings.alpaca_paper_trade),
        ),
        risk=RiskSettings(
            max_risk_per_trade_percent=float(runtime.get("MAX_RISK_PER_TRADE_PERCENT", 1.0)),
            max_daily_loss_percent=float(runtime.get("MAX_DAILY_LOSS_PERCENT", 2.0)),
            max_position_size_percent=float(runtime.get("MAX_POSITION_SIZE_PERCENT", 10.0)),
            min_reward_risk_ratio=float(runtime.get("MIN_REWARD_RISK_RATIO", 3.0)),
        ),
        llm_gateway=LlmGatewaySettings(
            llm_gateway_enable_paid_tests=runtime.get("LLM_GATEWAY_ENABLE_PAID_TESTS", settings.llm_gateway_enable_paid_tests),
            llm_gateway_daily_budget=runtime.get("LLM_GATEWAY_DAILY_BUDGET", settings.llm_gateway_daily_budget),
            llm_gateway_default_cheap_model=runtime.get("LLM_GATEWAY_DEFAULT_CHEAP_MODEL", settings.llm_gateway_default_cheap_model),
            llm_gateway_default_reasoning_model=runtime.get("LLM_GATEWAY_DEFAULT_REASONING_MODEL", settings.llm_gateway_default_reasoning_model),
            llm_gateway_default_fallback_model=runtime.get("LLM_GATEWAY_DEFAULT_FALLBACK_MODEL", settings.llm_gateway_default_fallback_model),
            embeddings_enable_paid_calls=runtime.get("EMBEDDINGS_ENABLE_PAID_CALLS", settings.embeddings_enable_paid_calls),
        ),
        market_data=MarketDataSettings(
            market_data_provider=runtime.get("MARKET_DATA_PROVIDER", settings.market_data_provider),
            market_data_provider_priority=runtime.get("MARKET_DATA_PROVIDER_PRIORITY", settings.market_data_provider_priority_raw),
            market_data_provider_timeout_seconds=runtime.get("MARKET_DATA_PROVIDER_TIMEOUT_SECONDS", settings.market_data_provider_timeout_seconds),
            alpaca_market_data_enabled=runtime.get("ALPACA_MARKET_DATA_ENABLED", settings.alpaca_market_data_enabled),
        ),
        news=NewsSettings(
            news_provider_enabled=runtime.get("NEWS_PROVIDER_ENABLED", settings.news_provider_enabled),
            news_provider_primary=runtime.get("NEWS_PROVIDER_PRIMARY", settings.news_provider_primary),
            news_provider_timeout_seconds=runtime.get("NEWS_PROVIDER_TIMEOUT_SECONDS", settings.news_provider_timeout_seconds),
        ),
        platform=PlatformFeatures(
            langsmith_tracing=runtime.get("LANGSMITH_TRACING", settings.langsmith_tracing),
            vector_memory_enabled=runtime.get("VECTOR_MEMORY_ENABLED", settings.vector_memory_enabled),
        ),
        rate_limits=RateLimitSettings(
            max_daily_llm_cost=runtime.get("MAX_DAILY_LLM_COST", settings.max_daily_llm_cost),
            max_daily_agent_runs=runtime.get("MAX_DAILY_AGENT_RUNS", settings.max_daily_agent_runs),
        ),
    )


def _apply_trading_updates(current: dict, updates: TradingSettingsUpdate | None) -> None:
    if updates is None:
        return
    if updates.paper_trading_enabled is not None:
        current["PAPER_TRADING_ENABLED"] = updates.paper_trading_enabled
    if updates.live_trading_enabled is not None:
        current["LIVE_TRADING_ENABLED"] = updates.live_trading_enabled
    if updates.broker_execution_enabled is not None:
        current["BROKER_EXECUTION_ENABLED"] = updates.broker_execution_enabled
    if updates.require_human_approval is not None:
        current["REQUIRE_HUMAN_APPROVAL"] = updates.require_human_approval
    if updates.execution_mode is not None:
        current["EXECUTION_MODE"] = updates.execution_mode
    if updates.execution_agent_enabled is not None:
        current["EXECUTION_AGENT_ENABLED"] = updates.execution_agent_enabled
    if updates.paper_starting_cash is not None:
        current["PAPER_STARTING_CASH"] = updates.paper_starting_cash
    if updates.broker_provider is not None:
        current["BROKER_PROVIDER"] = updates.broker_provider
    if updates.alpaca_paper_trade is not None:
        current["ALPACA_PAPER_TRADE"] = updates.alpaca_paper_trade


def _apply_llm_gateway_updates(current: dict, updates: LlmGatewaySettingsUpdate | None) -> None:
    if updates is None:
        return
    if updates.llm_gateway_enable_paid_tests is not None:
        current["LLM_GATEWAY_ENABLE_PAID_TESTS"] = updates.llm_gateway_enable_paid_tests
    if updates.llm_gateway_daily_budget is not None:
        current["LLM_GATEWAY_DAILY_BUDGET"] = updates.llm_gateway_daily_budget
    if updates.llm_gateway_default_cheap_model is not None:
        current["LLM_GATEWAY_DEFAULT_CHEAP_MODEL"] = updates.llm_gateway_default_cheap_model
    if updates.llm_gateway_default_reasoning_model is not None:
        current["LLM_GATEWAY_DEFAULT_REASONING_MODEL"] = updates.llm_gateway_default_reasoning_model
    if updates.llm_gateway_default_fallback_model is not None:
        current["LLM_GATEWAY_DEFAULT_FALLBACK_MODEL"] = updates.llm_gateway_default_fallback_model
    if updates.embeddings_enable_paid_calls is not None:
        current["EMBEDDINGS_ENABLE_PAID_CALLS"] = updates.embeddings_enable_paid_calls


def _apply_market_data_updates(current: dict, updates: MarketDataSettingsUpdate | None) -> None:
    if updates is None:
        return
    if updates.market_data_provider is not None:
        current["MARKET_DATA_PROVIDER"] = updates.market_data_provider
    if updates.market_data_provider_priority is not None:
        current["MARKET_DATA_PROVIDER_PRIORITY"] = updates.market_data_provider_priority
    if updates.market_data_provider_timeout_seconds is not None:
        current["MARKET_DATA_PROVIDER_TIMEOUT_SECONDS"] = updates.market_data_provider_timeout_seconds
    if updates.alpaca_market_data_enabled is not None:
        current["ALPACA_MARKET_DATA_ENABLED"] = updates.alpaca_market_data_enabled


def _apply_news_updates(current: dict, updates: NewsSettingsUpdate | None) -> None:
    if updates is None:
        return
    if updates.news_provider_enabled is not None:
        current["NEWS_PROVIDER_ENABLED"] = updates.news_provider_enabled
    if updates.news_provider_primary is not None:
        current["NEWS_PROVIDER_PRIMARY"] = updates.news_provider_primary
    if updates.news_provider_timeout_seconds is not None:
        current["NEWS_PROVIDER_TIMEOUT_SECONDS"] = updates.news_provider_timeout_seconds


def _apply_platform_updates(current: dict, updates: PlatformFeaturesUpdate | None) -> None:
    if updates is None:
        return
    if updates.langsmith_tracing is not None:
        current["LANGSMITH_TRACING"] = updates.langsmith_tracing
    if updates.vector_memory_enabled is not None:
        current["VECTOR_MEMORY_ENABLED"] = updates.vector_memory_enabled


def _apply_rate_limit_updates(current: dict, updates: RateLimitSettingsUpdate | None) -> None:
    if updates is None:
        return
    if updates.max_daily_llm_cost is not None:
        current["MAX_DAILY_LLM_COST"] = updates.max_daily_llm_cost
    if updates.max_daily_agent_runs is not None:
        current["MAX_DAILY_AGENT_RUNS"] = updates.max_daily_agent_runs


def _apply_risk_updates(current: dict, updates: RiskSettingsUpdate | None) -> None:
    if updates is None:
        return
    if updates.max_risk_per_trade_percent is not None:
        current["MAX_RISK_PER_TRADE_PERCENT"] = updates.max_risk_per_trade_percent
    if updates.max_daily_loss_percent is not None:
        current["MAX_DAILY_LOSS_PERCENT"] = updates.max_daily_loss_percent
    if updates.max_position_size_percent is not None:
        current["MAX_POSITION_SIZE_PERCENT"] = updates.max_position_size_percent
    if updates.min_reward_risk_ratio is not None:
        current["MIN_REWARD_RISK_RATIO"] = updates.min_reward_risk_ratio


@router.post("/settings", response_model=SettingsResponse)
def update_settings(request: SettingsUpdateRequest) -> SettingsResponse:
    """Update runtime settings.
    
    Changes are persisted to runtime_settings.json and take effect immediately.
    Safety checks prevent unsafe combinations (e.g., live trading without approval).
    """
    current = load_runtime_settings()
    
    # Apply updates by category
    _apply_trading_updates(current, request.trading)
    _apply_risk_updates(current, request.risk)
    _apply_llm_gateway_updates(current, request.llm_gateway)
    _apply_market_data_updates(current, request.market_data)
    _apply_news_updates(current, request.news)
    _apply_platform_updates(current, request.platform)
    _apply_rate_limit_updates(current, request.rate_limits)
    
    # Safety validation
    if current.get("LIVE_TRADING_ENABLED") and not current.get("REQUIRE_HUMAN_APPROVAL"):
        raise HTTPException(
            status_code=400,
            detail="Cannot enable live trading without human approval requirement"
        )
    
    if current.get("BROKER_EXECUTION_ENABLED") and not current.get("REQUIRE_HUMAN_APPROVAL"):
        raise HTTPException(
            status_code=400,
            detail="Cannot enable broker execution without human approval requirement"
        )
    
    save_runtime_settings(current)
    
    # Return updated settings
    return get_settings()


@router.post("/settings/reset")
def reset_settings() -> SettingsResponse:
    """Reset all runtime settings to defaults from .env."""
    if RUNTIME_SETTINGS_FILE.exists():
        RUNTIME_SETTINGS_FILE.unlink()
    return get_settings()
