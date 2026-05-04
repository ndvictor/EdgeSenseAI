from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

import requests
from pydantic import BaseModel, Field

from app.core.settings import settings


ExecutionMode = Literal["disabled", "dry_run", "paper", "live"]
OrderSide = Literal["buy", "sell"]
OrderType = Literal["market", "limit", "stop", "stop_limit"]
TimeInForce = Literal["day", "gtc", "opg", "cls", "ioc", "fok"]


class TradeNowConfig(BaseModel):
    user_enabled: bool = False
    execution_mode: ExecutionMode = "dry_run"
    broker: str = "alpaca"
    paper_endpoint: str = "https://paper-api.alpaca.markets"
    live_endpoint: str = "https://api.alpaca.markets"
    require_human_approval: bool = True
    live_trading_enabled_env: bool = False
    broker_execution_enabled_env: bool = False
    paper_trading_enabled_env: bool = True
    alpaca_keys_configured: bool = False
    alpaca_key_id_configured: bool = False
    alpaca_secret_key_configured: bool = False
    status: str = "disabled_by_default"
    blockers: list[str] = Field(default_factory=list)
    safety_notes: list[str] = Field(default_factory=list)


class TradeNowConfigUpdate(BaseModel):
    user_enabled: bool = False
    execution_mode: ExecutionMode = "dry_run"


class TradeNowOrderRequest(BaseModel):
    symbol: str
    side: OrderSide
    qty: float | None = None
    notional: float | None = None
    type: OrderType = "market"
    time_in_force: TimeInForce = "day"
    limit_price: float | None = None
    stop_price: float | None = None
    dry_run: bool = True
    human_approval_confirmed: bool = False
    client_order_id: str | None = None


class TradeNowOrderResponse(BaseModel):
    status: Literal["blocked", "dry_run", "submitted", "failed"]
    broker: str = "alpaca"
    execution_mode: ExecutionMode
    order_id: str | None = None
    client_order_id: str
    symbol: str
    side: str
    submitted_payload: dict[str, Any]
    broker_response: dict[str, Any] | None = None
    request_id: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    safety_notes: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


_CONFIG = TradeNowConfig()
_LAST_ORDER: TradeNowOrderResponse | None = None


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _alpaca_key_id() -> str:
    return os.getenv("ALPACA_API_KEY") or os.getenv("APCA_API_KEY_ID") or settings.alpaca_api_key


def _alpaca_secret_key() -> str:
    return os.getenv("ALPACA_SECRET_KEY") or os.getenv("APCA_API_SECRET_KEY") or settings.alpaca_secret_key


def _paper_base_url() -> str:
    return os.getenv("ALPACA_PAPER_TRADING_BASE_URL") or os.getenv("APCA_API_BASE_URL") or "https://paper-api.alpaca.markets"


def _live_base_url() -> str:
    return os.getenv("ALPACA_LIVE_TRADING_BASE_URL") or "https://api.alpaca.markets"


def _refresh_config() -> TradeNowConfig:
    key_id = _alpaca_key_id()
    secret = _alpaca_secret_key()
    blockers: list[str] = []
    execution_enabled = _env_bool("BROKER_EXECUTION_ENABLED", settings.execution_agent_enabled)
    live_enabled = _env_bool("LIVE_TRADING_ENABLED", settings.live_trading_enabled)
    paper_enabled = _env_bool("PAPER_TRADING_ENABLED", settings.paper_trading_enabled)

    if not _CONFIG.user_enabled:
        blockers.append("TradeNow UI toggle is disabled.")
    if _CONFIG.execution_mode == "live" and not live_enabled:
        blockers.append("LIVE_TRADING_ENABLED is false, so live orders are blocked.")
    if _CONFIG.execution_mode == "paper" and not paper_enabled:
        blockers.append("PAPER_TRADING_ENABLED is false, so paper orders are blocked.")
    if not execution_enabled:
        blockers.append("BROKER_EXECUTION_ENABLED/EXECUTION_AGENT_ENABLED is false, so broker submission is blocked.")
    if not key_id or not secret:
        blockers.append("Alpaca API key and secret are not configured in backend environment variables.")

    status = "ready_for_paper_submission" if not blockers and _CONFIG.execution_mode == "paper" else "blocked"
    if _CONFIG.execution_mode == "dry_run":
        status = "dry_run_ready"

    _CONFIG.paper_endpoint = _paper_base_url()
    _CONFIG.live_endpoint = _live_base_url()
    _CONFIG.require_human_approval = True
    _CONFIG.live_trading_enabled_env = live_enabled
    _CONFIG.broker_execution_enabled_env = execution_enabled
    _CONFIG.paper_trading_enabled_env = paper_enabled
    _CONFIG.alpaca_key_id_configured = bool(key_id)
    _CONFIG.alpaca_secret_key_configured = bool(secret)
    _CONFIG.alpaca_keys_configured = bool(key_id and secret)
    _CONFIG.blockers = blockers
    _CONFIG.status = status
    _CONFIG.safety_notes = [
        "TradeNow is disabled by default.",
        "API keys must be configured server-side via environment variables, not saved in the browser.",
        "Dry-run is the default mode and does not contact Alpaca.",
        "Paper mode can submit only when user toggle, env flags, keys, and human approval are all present.",
        "Live mode is blocked unless LIVE_TRADING_ENABLED and BROKER_EXECUTION_ENABLED are explicitly true.",
    ]
    return _CONFIG


def get_trade_now_config() -> TradeNowConfig:
    return _refresh_config()


def update_trade_now_config(update: TradeNowConfigUpdate) -> TradeNowConfig:
    _CONFIG.user_enabled = update.user_enabled
    if update.execution_mode == "live" and not _env_bool("LIVE_TRADING_ENABLED", settings.live_trading_enabled):
        _CONFIG.execution_mode = "disabled"
    else:
        _CONFIG.execution_mode = update.execution_mode
    return _refresh_config()


def _order_payload(request: TradeNowOrderRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "symbol": request.symbol.upper().strip(),
        "side": request.side,
        "type": request.type,
        "time_in_force": request.time_in_force,
        "client_order_id": request.client_order_id or f"edgesense-{uuid4().hex[:18]}",
    }
    if request.qty is not None:
        payload["qty"] = str(request.qty)
    if request.notional is not None:
        payload["notional"] = str(request.notional)
    if request.limit_price is not None:
        payload["limit_price"] = str(request.limit_price)
    if request.stop_price is not None:
        payload["stop_price"] = str(request.stop_price)
    return payload


def _validate_order_request(request: TradeNowOrderRequest, config: TradeNowConfig) -> list[str]:
    blockers: list[str] = []
    if not request.symbol.strip():
        blockers.append("Symbol is required.")
    if request.qty is None and request.notional is None:
        blockers.append("Either qty or notional is required.")
    if request.qty is not None and request.notional is not None:
        blockers.append("Use qty or notional, not both.")
    if request.qty is not None and request.qty <= 0:
        blockers.append("qty must be greater than zero.")
    if request.notional is not None and request.notional <= 0:
        blockers.append("notional must be greater than zero.")
    if request.type in {"limit", "stop_limit"} and request.limit_price is None:
        blockers.append("limit_price is required for limit and stop_limit orders.")
    if request.type in {"stop", "stop_limit"} and request.stop_price is None:
        blockers.append("stop_price is required for stop and stop_limit orders.")
    if not request.human_approval_confirmed:
        blockers.append("Human approval checkbox is required before any broker submission.")
    if config.execution_mode == "disabled":
        blockers.append("Execution mode is disabled.")
    if not config.user_enabled:
        blockers.append("TradeNow UI toggle is disabled.")
    return blockers


def place_trade_now_order(request: TradeNowOrderRequest) -> TradeNowOrderResponse:
    global _LAST_ORDER
    config = _refresh_config()
    payload = _order_payload(request)
    client_order_id = payload["client_order_id"]
    blockers = _validate_order_request(request, config)
    warnings = [
        "This endpoint is an execution foundation. Keep paper/dry-run until separately promoted.",
        "Alpaca paper trading simulates fills and may differ from live trading.",
    ]

    effective_dry_run = request.dry_run or config.execution_mode in {"disabled", "dry_run"}
    if effective_dry_run:
        response = TradeNowOrderResponse(
            status="dry_run" if not blockers else "blocked",
            execution_mode=config.execution_mode,
            client_order_id=client_order_id,
            symbol=payload["symbol"],
            side=request.side,
            submitted_payload=payload,
            blockers=blockers,
            warnings=warnings,
            safety_notes=config.safety_notes,
        )
        _LAST_ORDER = response
        return response

    blockers.extend(config.blockers)
    if config.execution_mode == "live" and not config.live_trading_enabled_env:
        blockers.append("Live mode requested but LIVE_TRADING_ENABLED is false.")
    if blockers:
        response = TradeNowOrderResponse(
            status="blocked",
            execution_mode=config.execution_mode,
            client_order_id=client_order_id,
            symbol=payload["symbol"],
            side=request.side,
            submitted_payload=payload,
            blockers=sorted(set(blockers)),
            warnings=warnings,
            safety_notes=config.safety_notes,
        )
        _LAST_ORDER = response
        return response

    base_url = config.live_endpoint if config.execution_mode == "live" else config.paper_endpoint
    url = f"{base_url.rstrip('/')}/v2/orders"
    headers = {
        "APCA-API-KEY-ID": _alpaca_key_id(),
        "APCA-API-SECRET-KEY": _alpaca_secret_key(),
        "Content-Type": "application/json",
    }
    try:
        broker_response = requests.post(url, json=payload, headers=headers, timeout=10)
        request_id = broker_response.headers.get("X-Request-ID")
        try:
            body = broker_response.json()
        except Exception:
            body = {"raw_text": broker_response.text}
        if broker_response.status_code >= 400:
            response = TradeNowOrderResponse(
                status="failed",
                execution_mode=config.execution_mode,
                client_order_id=client_order_id,
                symbol=payload["symbol"],
                side=request.side,
                submitted_payload=payload,
                broker_response=body,
                request_id=request_id,
                blockers=[f"Alpaca returned HTTP {broker_response.status_code}"],
                warnings=warnings,
                safety_notes=config.safety_notes,
            )
        else:
            response = TradeNowOrderResponse(
                status="submitted",
                execution_mode=config.execution_mode,
                order_id=body.get("id"),
                client_order_id=client_order_id,
                symbol=payload["symbol"],
                side=request.side,
                submitted_payload=payload,
                broker_response=body,
                request_id=request_id,
                warnings=warnings,
                safety_notes=config.safety_notes,
            )
    except Exception as exc:
        response = TradeNowOrderResponse(
            status="failed",
            execution_mode=config.execution_mode,
            client_order_id=client_order_id,
            symbol=payload["symbol"],
            side=request.side,
            submitted_payload=payload,
            blockers=[str(exc)],
            warnings=warnings,
            safety_notes=config.safety_notes,
        )
    _LAST_ORDER = response
    return response


def get_last_trade_now_order() -> TradeNowOrderResponse | dict[str, Any]:
    return _LAST_ORDER or {"status": "not_found", "message": "No TradeNow order has been attempted this session."}
