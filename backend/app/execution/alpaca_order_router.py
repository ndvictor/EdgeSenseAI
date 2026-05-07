"""Low-level Alpaca REST submit (paper or live base URL)."""

from __future__ import annotations

import os
from typing import Any, Literal

import requests

from app.core.effective_runtime import effective_bool
from app.execution.edgesense_execution_config import load_edgesense_execution_config


def _keys() -> tuple[str, str]:
    key = os.getenv("ALPACA_API_KEY_ID") or os.getenv("ALPACA_API_KEY") or os.getenv("APCA_API_KEY_ID") or ""
    sec = os.getenv("ALPACA_API_SECRET_KEY") or os.getenv("ALPACA_SECRET_KEY") or os.getenv("APCA_API_SECRET_KEY") or ""
    return key, sec


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


def submit_alpaca_order(
    payload: dict[str, Any],
    *,
    mode: Literal["paper", "live"],
    timeout_seconds: int | None = None,
) -> tuple[int, dict[str, Any], str | None]:
    """Returns status_code, body dict, x_request_id."""
    cfg = load_edgesense_execution_config()
    timeout = timeout_seconds or cfg.order_timeout_seconds
    key, sec = _keys()
    if not key or not sec:
        return 0, {"error": "alpaca_keys_missing"}, None

    # Master Admin safety gates (runtime-aware)
    if effective_bool("EMERGENCY_STOP"):
        return 0, {"error": "emergency_stop_active"}, None
    if not effective_bool("EXECUTION_ENABLED"):
        return 0, {"error": "execution_disabled"}, None
    if not effective_bool("BROKER_EXECUTION_ENABLED"):
        return 0, {"error": "broker_execution_disabled"}, None

    if mode == "paper":
        if not effective_bool("PAPER_TRADING_ENABLED"):
            return 0, {"error": "paper_trading_disabled"}, None
        base = (
            os.getenv("ALPACA_PAPER_TRADING_BASE_URL")
            or os.getenv("APCA_API_BASE_URL")
            or "https://paper-api.alpaca.markets"
        ).rstrip("/")
    else:
        if not effective_bool("LIVE_TRADING_ENABLED") or not cfg.live_trading_enabled:
            return 0, {"error": "live_trading_disabled"}, None
        base = os.getenv("ALPACA_LIVE_TRADING_BASE_URL") or "https://api.alpaca.markets"
        base = base.rstrip("/")

    url = f"{base}/v2/orders"
    headers = {
        "APCA-API-KEY-ID": key,
        "APCA-API-SECRET-KEY": sec,
        "Content-Type": "application/json",
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=timeout)
        rid = r.headers.get("X-Request-ID")
        try:
            body = r.json()
        except Exception:
            body = {"raw": r.text[:500]}
        return r.status_code, body, rid
    except requests.RequestException as exc:
        return 0, {"error": str(exc)[:200]}, None
