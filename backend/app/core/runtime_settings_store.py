"""Persistent runtime settings (runtime_settings.json) shared by API and services."""

import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException

# backend/runtime_settings.json
RUNTIME_SETTINGS_FILE = Path(__file__).resolve().parent.parent.parent / "runtime_settings.json"

DEFAULT_RUNTIME_SETTINGS: dict[str, Any] = {
    # Trading Settings
    "PAPER_TRADING_ENABLED": True,
    "LIVE_TRADING_ENABLED": False,
    "BROKER_EXECUTION_ENABLED": False,
    "REQUIRE_HUMAN_APPROVAL": True,
    "EXECUTION_MODE": "dry_run",
    "EXECUTION_AGENT_ENABLED": False,
    "PAPER_STARTING_CASH": 100000.0,
    "BROKER_PROVIDER": "alpaca",
    "ALPACA_PAPER_TRADE": True,
    # Platform Features
    "LANGSMITH_TRACING": True,
    "VECTOR_MEMORY_ENABLED": True,
    # LLM Gateway Settings
    "LLM_GATEWAY_ENABLE_PAID_TESTS": False,
    "LLM_GATEWAY_DAILY_BUDGET": 10.0,
    "LLM_GATEWAY_DEFAULT_CHEAP_MODEL": "gpt-4o-mini",
    "LLM_GATEWAY_DEFAULT_REASONING_MODEL": "gpt-4o",
    "LLM_GATEWAY_DEFAULT_FALLBACK_MODEL": "local-placeholder",
    "EMBEDDINGS_ENABLE_PAID_CALLS": False,
    # Market Data Settings
    "MARKET_DATA_PROVIDER": "mock",
    "MARKET_DATA_PROVIDER_PRIORITY": "alpaca,yfinance,mock",
    "MARKET_DATA_PROVIDER_TIMEOUT_SECONDS": 10,
    "ALPACA_MARKET_DATA_ENABLED": False,
    # News Settings
    "NEWS_PROVIDER_ENABLED": False,
    "NEWS_PROVIDER_PRIMARY": "none",
    "NEWS_PROVIDER_TIMEOUT_SECONDS": 10,
    # Rate Limits
    "MAX_DAILY_LLM_COST": 10,
    "MAX_DAILY_AGENT_RUNS": 500,
}


def load_runtime_settings() -> dict[str, Any]:
    """Load runtime settings from file, merged with defaults for any missing keys."""
    if RUNTIME_SETTINGS_FILE.exists():
        try:
            with open(RUNTIME_SETTINGS_FILE, "r", encoding="utf-8") as f:
                stored = json.load(f)
                return {**DEFAULT_RUNTIME_SETTINGS, **stored}
        except (json.JSONDecodeError, OSError):
            pass
    return DEFAULT_RUNTIME_SETTINGS.copy()


def save_runtime_settings(settings_dict: dict[str, Any]) -> None:
    """Persist full runtime settings dict to disk."""
    try:
        with open(RUNTIME_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings_dict, f, indent=2)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {e}") from e
