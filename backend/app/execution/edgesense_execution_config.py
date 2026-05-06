"""EDGESENSE_* environment configuration — paper-first, live opt-in."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    v = os.getenv(name)
    if v is None or not v.strip():
        return default
    try:
        return float(v)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None or not v.strip():
        return default
    try:
        return int(float(v))
    except ValueError:
        return default


def _parse_asset_classes(raw: str) -> frozenset[str]:
    parts = [p.strip().lower() for p in raw.split(",") if p.strip()]
    out: set[str] = set()
    for p in parts:
        if p in {"stocks", "stock"}:
            out.add("stock")
        elif p in {"options", "option"}:
            out.add("option")
        elif p in {"crypto"}:
            out.add("crypto")
    return frozenset(out or {"stock", "option", "crypto"})


@dataclass(frozen=True)
class EdgeSenseExecutionConfig:
    execution_mode: str
    live_trading_enabled: bool
    require_human_approval: bool
    max_daily_loss_pct: float
    max_trade_risk_pct: float
    max_open_positions: int
    max_symbol_exposure_pct: float
    allowed_asset_classes: frozenset[str]
    default_order_type: str
    max_spread_pct: float
    max_slippage_pct: float
    order_timeout_seconds: int


@lru_cache
def load_edgesense_execution_config() -> EdgeSenseExecutionConfig:
    mode = (os.getenv("EDGESENSE_EXECUTION_MODE") or "paper").strip().lower()
    if mode not in {"paper", "simulated", "live_disabled", "live"}:
        mode = "paper"
    return EdgeSenseExecutionConfig(
        execution_mode=mode,
        live_trading_enabled=_env_bool("EDGESENSE_LIVE_TRADING_ENABLED", False),
        require_human_approval=_env_bool("EDGESENSE_REQUIRE_HUMAN_APPROVAL", True),
        max_daily_loss_pct=_env_float("EDGESENSE_MAX_DAILY_LOSS_PCT", 2.0),
        max_trade_risk_pct=_env_float("EDGESENSE_MAX_TRADE_RISK_PCT", 0.5),
        max_open_positions=_env_int("EDGESENSE_MAX_OPEN_POSITIONS", 3),
        max_symbol_exposure_pct=_env_float("EDGESENSE_MAX_SYMBOL_EXPOSURE_PCT", 20.0),
        allowed_asset_classes=_parse_asset_classes(os.getenv("EDGESENSE_ALLOWED_ASSET_CLASSES") or "stocks,options,crypto"),
        default_order_type=(os.getenv("EDGESENSE_DEFAULT_ORDER_TYPE") or "limit").strip().lower(),
        max_spread_pct=_env_float("EDGESENSE_MAX_SPREAD_PCT", 0.5),
        max_slippage_pct=_env_float("EDGESENSE_MAX_SLIPPAGE_PCT", 0.25),
        order_timeout_seconds=_env_int("EDGESENSE_ORDER_TIMEOUT_SECONDS", 60),
    )


def edgesense_config_summary() -> dict:
    c = load_edgesense_execution_config()
    return {
        "execution_mode": c.execution_mode,
        "live_trading_enabled": c.live_trading_enabled,
        "require_human_approval": c.require_human_approval,
        "max_daily_loss_pct": c.max_daily_loss_pct,
        "max_trade_risk_pct": c.max_trade_risk_pct,
        "max_open_positions": c.max_open_positions,
        "max_symbol_exposure_pct": c.max_symbol_exposure_pct,
        "allowed_asset_classes": sorted(c.allowed_asset_classes),
        "default_order_type": c.default_order_type,
        "max_spread_pct": c.max_spread_pct,
        "max_slippage_pct": c.max_slippage_pct,
        "order_timeout_seconds": c.order_timeout_seconds,
    }
