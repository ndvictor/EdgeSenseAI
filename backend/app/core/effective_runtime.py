"""Effective configuration: runtime_settings.json overrides process env overrides pydantic defaults."""

from __future__ import annotations

import os
from typing import Any

from app.core.production_safety import is_production_environment
from app.core.runtime_settings_store import load_runtime_settings
from app.core.settings import settings


_PRODUCTION_ENV_FIRST_KEYS = {
    "PAPER_TRADING_ENABLED",
    "LIVE_TRADING_ENABLED",
    "BROKER_EXECUTION_ENABLED",
    "EXECUTION_AGENT_ENABLED",
    "REQUIRE_HUMAN_APPROVAL",
    "MARKET_DATA_MODE",
    "MARKET_DATA_PROVIDER",
    "MARKET_DATA_PROVIDER_PRIORITY",
    "ALLOW_MOCK_MARKET_DATA",
    "ALLOW_SYNTHETIC_MARKET_DATA",
    "QLIB_REQUIRED",
}

# Uppercase env keys -> Settings attribute name for fallback when env is unset
_BOOL_ENV_TO_SETTINGS: dict[str, str] = {
    "WORKFLOW_ENABLED": "",
    "WORKFLOW_RUNNING": "",
    "EXECUTION_ENABLED": "",
    "EMERGENCY_STOP": "",
    "FORCE_CLOSE_REQUESTED": "",
    "MASTER_ADMIN_MODE": "",
    "PAPER_TRADING_ENABLED": "paper_trading_enabled",
    "LIVE_TRADING_ENABLED": "live_trading_enabled",
    "BROKER_EXECUTION_ENABLED": "broker_execution_enabled",
    "REQUIRE_HUMAN_APPROVAL": "require_human_approval",
    "EXECUTION_AGENT_ENABLED": "execution_agent_enabled",
    "ALPACA_PAPER_TRADE": "alpaca_paper_trade",
    "LANGSMITH_TRACING": "langsmith_tracing",
    "VECTOR_MEMORY_ENABLED": "vector_memory_enabled",
    "LLM_GATEWAY_ENABLE_PAID_TESTS": "llm_gateway_enable_paid_tests",
    "EMBEDDINGS_ENABLE_PAID_CALLS": "embeddings_enable_paid_calls",
    "ALPACA_MARKET_DATA_ENABLED": "alpaca_market_data_enabled",
    "ALLOW_MOCK_MARKET_DATA": "allow_mock_market_data",
    "ALLOW_SYNTHETIC_MARKET_DATA": "allow_synthetic_market_data",
    "NEWS_PROVIDER_ENABLED": "news_provider_enabled",
}

_FLOAT_ENV_TO_SETTINGS: dict[str, str] = {
    "LLM_GATEWAY_DAILY_BUDGET": "llm_gateway_daily_budget",
    "PAPER_STARTING_CASH": "paper_starting_cash",
    "MAX_DAILY_LLM_COST": "max_daily_llm_cost",
}

_INT_ENV_TO_SETTINGS: dict[str, str] = {
    "MARKET_DATA_PROVIDER_TIMEOUT_SECONDS": "market_data_provider_timeout_seconds",
    "NEWS_PROVIDER_TIMEOUT_SECONDS": "news_provider_timeout_seconds",
    "MAX_DAILY_AGENT_RUNS": "max_daily_agent_runs",
}

_STR_ENV_TO_SETTINGS: dict[str, str] = {
    "EXECUTION_MODE": "execution_mode",
    "BROKER_PROVIDER": "broker_provider",
    "MARKET_DATA_MODE": "market_data_mode",
    "MARKET_DATA_PROVIDER": "market_data_provider",
    "MARKET_DATA_PROVIDER_PRIORITY": "market_data_provider_priority_raw",
    "NEWS_PROVIDER_PRIMARY": "news_provider_primary",
    "NEWS_PROVIDER_PRIORITY": "news_provider_priority_raw",
    "LLM_GATEWAY_DEFAULT_CHEAP_MODEL": "llm_gateway_default_cheap_model",
    "LLM_GATEWAY_DEFAULT_REASONING_MODEL": "llm_gateway_default_reasoning_model",
    "LLM_GATEWAY_DEFAULT_FALLBACK_MODEL": "llm_gateway_default_fallback_model",
}


def _parse_env_bool(raw: str) -> bool:
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def effective_bool(env_key: str) -> bool:
    """Resolve bool: runtime_settings.json > os.environ > pydantic settings."""
    env_val = os.getenv(env_key)
    if is_production_environment() and env_key in _PRODUCTION_ENV_FIRST_KEYS and env_val is not None:
        return _parse_env_bool(env_val)
    runtime = load_runtime_settings()
    if env_key in runtime:
        return bool(runtime[env_key])
    if env_val is not None:
        return _parse_env_bool(env_val)
    attr = _BOOL_ENV_TO_SETTINGS.get(env_key)
    if attr:
        return bool(getattr(settings, attr))
    return False


def effective_float(env_key: str) -> float:
    runtime = load_runtime_settings()
    if env_key in runtime:
        return float(runtime[env_key])
    env_val = os.getenv(env_key)
    if env_val is not None:
        try:
            return float(env_val)
        except ValueError:
            pass
    attr = _FLOAT_ENV_TO_SETTINGS.get(env_key)
    if attr:
        return float(getattr(settings, attr))
    return 0.0


def effective_int(env_key: str) -> int:
    runtime = load_runtime_settings()
    if env_key in runtime:
        return int(runtime[env_key])
    env_val = os.getenv(env_key)
    if env_val is not None:
        try:
            return int(env_val)
        except ValueError:
            pass
    attr = _INT_ENV_TO_SETTINGS.get(env_key)
    if attr:
        return int(getattr(settings, attr))
    return 0


def effective_str(env_key: str) -> str:
    env_val = os.getenv(env_key)
    if is_production_environment() and env_key in _PRODUCTION_ENV_FIRST_KEYS and env_val is not None:
        return env_val
    runtime = load_runtime_settings()
    if env_key in runtime:
        return str(runtime[env_key])
    if env_val is not None:
        return env_val
    attr = _STR_ENV_TO_SETTINGS.get(env_key)
    if attr:
        return str(getattr(settings, attr))
    return ""


def broker_or_agent_execution_enabled() -> bool:
    """True when either broker execution or execution agent is enabled (runtime-aware)."""
    return effective_bool("BROKER_EXECUTION_ENABLED") or effective_bool("EXECUTION_AGENT_ENABLED")


def emergency_stop_active() -> bool:
    return effective_bool("EMERGENCY_STOP")


def execution_enabled() -> bool:
    return effective_bool("EXECUTION_ENABLED") and not emergency_stop_active()


def news_provider_priority_from_runtime() -> list[str]:
    """Comma-separated fallback order from runtime / env / defaults (lowercase names)."""
    raw = effective_str("NEWS_PROVIDER_PRIORITY")
    if raw and raw.strip():
        return [p.strip().lower() for p in raw.split(",") if p.strip()]
    return list(settings.news_provider_priority)


def news_provider_chain() -> list[str]:
    """News feeds to try in order: primary first, then priority list entries (deduped)."""
    primary = (effective_str("NEWS_PROVIDER_PRIMARY") or "").lower().strip()
    tail = news_provider_priority_from_runtime()
    ordered: list[str] = []
    seen: set[str] = set()
    if primary and primary != "none":
        ordered.append(primary)
        seen.add(primary)
    for name in tail:
        n = (name or "").strip().lower()
        if not n or n == "none" or n in seen:
            continue
        ordered.append(n)
        seen.add(n)
    return ordered if ordered else ["none"]
