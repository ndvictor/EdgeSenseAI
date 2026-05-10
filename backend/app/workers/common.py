from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from uuid import uuid4


def setup_worker_logging() -> None:
    logging.basicConfig(level=os.environ.get("WORKER_LOG_LEVEL", "INFO"), format="%(message)s")


def get_worker_run_id(prefix: str) -> str:
    safe_prefix = (prefix or "worker").strip().lower().replace("_", "-")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{safe_prefix}-{stamp}-{uuid4().hex[:8]}"


def env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return bool(default)
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def require_production_data_policy() -> None:
    environment = (os.environ.get("ENVIRONMENT") or os.environ.get("APP_ENV") or "").strip().lower()
    market_data_mode = (os.environ.get("MARKET_DATA_MODE") or "").strip().lower()
    blockers: list[str] = []
    if environment not in {"prod", "production"}:
        blockers.append("environment_not_production")
    if market_data_mode not in {"provider", "runtime"}:
        blockers.append("market_data_mode_must_be_provider_or_runtime")
    if env_bool("ALLOW_SYNTHETIC_MARKET_DATA", False):
        blockers.append("synthetic_market_data_enabled")
    if env_bool("LIVE_TRADING_ENABLED", False):
        blockers.append("live_trading_enabled")
    if env_bool("BROKER_EXECUTION_ENABLED", False):
        blockers.append("broker_execution_enabled")
    if blockers:
        raise RuntimeError(",".join(blockers))


def print_summary(summary: dict) -> None:
    print(json.dumps(summary, sort_keys=True, default=str), flush=True)


def clean_symbols(values: list[str] | tuple[str, ...] | None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        symbol = str(value or "").strip().upper()
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        out.append(symbol)
    return out
