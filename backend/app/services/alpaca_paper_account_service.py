from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

import requests
from pydantic import BaseModel, Field

from app.core.effective_runtime import broker_or_agent_execution_enabled, effective_bool
from app.core.settings import settings


AlpacaConnectionStatus = Literal["connected", "not_configured", "unavailable"]


class AlpacaPaperAccount(BaseModel):
    id: str | None = None
    account_number: str | None = None
    status: str | None = None
    currency: str | None = None
    cash: float | None = None
    buying_power: float | None = None
    portfolio_value: float | None = None
    equity: float | None = None
    last_equity: float | None = None
    daytrade_count: int | None = None
    pattern_day_trader: bool | None = None
    trading_blocked: bool | None = None
    transfers_blocked: bool | None = None
    account_blocked: bool | None = None


class AlpacaPaperPosition(BaseModel):
    symbol: str
    qty: float | None = None
    side: str | None = None
    market_value: float | None = None
    cost_basis: float | None = None
    unrealized_pl: float | None = None
    unrealized_plpc: float | None = None
    current_price: float | None = None
    avg_entry_price: float | None = None


class AlpacaPaperOrder(BaseModel):
    id: str
    client_order_id: str | None = None
    symbol: str
    side: str | None = None
    type: str | None = None
    status: str | None = None
    qty: float | None = None
    notional: float | None = None
    filled_qty: float | None = None
    submitted_at: str | None = None
    filled_at: str | None = None
    limit_price: float | None = None
    stop_price: float | None = None


class AlpacaPaperSnapshot(BaseModel):
    provider: str = "alpaca"
    mode: str = "paper"
    status: AlpacaConnectionStatus
    endpoint: str
    keys_configured: bool
    paper_trading_enabled: bool
    live_trading_enabled: bool
    broker_execution_enabled: bool
    account: AlpacaPaperAccount | None = None
    positions: list[AlpacaPaperPosition] = Field(default_factory=list)
    open_orders: list[AlpacaPaperOrder] = Field(default_factory=list)
    message: str
    warnings: list[str] = Field(default_factory=list)
    last_checked: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def _alpaca_key_id() -> str:
    import os

    return (
        os.getenv("ALPACA_API_KEY_ID")
        or os.getenv("ALPACA_API_KEY")
        or os.getenv("APCA_API_KEY_ID")
        or settings.alpaca_api_key
    )


def _alpaca_secret_key() -> str:
    import os

    return (
        os.getenv("ALPACA_API_SECRET_KEY")
        or os.getenv("ALPACA_SECRET_KEY")
        or os.getenv("APCA_API_SECRET_KEY")
        or settings.alpaca_secret_key
    )


def _paper_base_url() -> str:
    import os

    return (
        os.getenv("ALPACA_PAPER_TRADING_BASE_URL")
        or os.getenv("APCA_API_BASE_URL")
        or "https://paper-api.alpaca.markets"
    ).rstrip("/")


def _headers() -> dict[str, str]:
    return {
        "APCA-API-KEY-ID": _alpaca_key_id(),
        "APCA-API-SECRET-KEY": _alpaca_secret_key(),
    }


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _account(payload: dict[str, Any]) -> AlpacaPaperAccount:
    return AlpacaPaperAccount(
        id=payload.get("id"),
        account_number=payload.get("account_number"),
        status=payload.get("status"),
        currency=payload.get("currency"),
        cash=_float(payload.get("cash")),
        buying_power=_float(payload.get("buying_power")),
        portfolio_value=_float(payload.get("portfolio_value")),
        equity=_float(payload.get("equity")),
        last_equity=_float(payload.get("last_equity")),
        daytrade_count=_int(payload.get("daytrade_count")),
        pattern_day_trader=payload.get("pattern_day_trader"),
        trading_blocked=payload.get("trading_blocked"),
        transfers_blocked=payload.get("transfers_blocked"),
        account_blocked=payload.get("account_blocked"),
    )


def _position(payload: dict[str, Any]) -> AlpacaPaperPosition:
    return AlpacaPaperPosition(
        symbol=str(payload.get("symbol") or "").upper(),
        qty=_float(payload.get("qty")),
        side=payload.get("side"),
        market_value=_float(payload.get("market_value")),
        cost_basis=_float(payload.get("cost_basis")),
        unrealized_pl=_float(payload.get("unrealized_pl")),
        unrealized_plpc=_float(payload.get("unrealized_plpc")),
        current_price=_float(payload.get("current_price")),
        avg_entry_price=_float(payload.get("avg_entry_price")),
    )


def _order(payload: dict[str, Any]) -> AlpacaPaperOrder:
    return AlpacaPaperOrder(
        id=str(payload.get("id") or ""),
        client_order_id=payload.get("client_order_id"),
        symbol=str(payload.get("symbol") or "").upper(),
        side=payload.get("side"),
        type=payload.get("type"),
        status=payload.get("status"),
        qty=_float(payload.get("qty")),
        notional=_float(payload.get("notional")),
        filled_qty=_float(payload.get("filled_qty")),
        submitted_at=payload.get("submitted_at"),
        filled_at=payload.get("filled_at"),
        limit_price=_float(payload.get("limit_price")),
        stop_price=_float(payload.get("stop_price")),
    )


def get_alpaca_paper_snapshot() -> AlpacaPaperSnapshot:
    endpoint = _paper_base_url()
    keys_configured = bool(_alpaca_key_id() and _alpaca_secret_key())
    paper_enabled = effective_bool("PAPER_TRADING_ENABLED")
    live_enabled = effective_bool("LIVE_TRADING_ENABLED")
    broker_enabled = broker_or_agent_execution_enabled()
    warnings = [
        "This endpoint reads Alpaca paper account state only.",
        "Live trading remains disabled unless LIVE_TRADING_ENABLED is explicitly true.",
        "Broker order submission still goes through TradeNow safety gates.",
    ]

    if not keys_configured:
        return AlpacaPaperSnapshot(
            status="not_configured",
            endpoint=endpoint,
            keys_configured=False,
            paper_trading_enabled=paper_enabled,
            live_trading_enabled=live_enabled,
            broker_execution_enabled=broker_enabled,
            message="Alpaca API key and secret are not configured in the backend environment.",
            warnings=warnings,
        )

    try:
        account_response = requests.get(f"{endpoint}/v2/account", headers=_headers(), timeout=10)
        request_id = account_response.headers.get("X-Request-ID")
        if account_response.status_code >= 400:
            detail = account_response.text[:240]
            if request_id:
                detail = f"{detail} (request {request_id})"
            return AlpacaPaperSnapshot(
                status="unavailable",
                endpoint=endpoint,
                keys_configured=True,
                paper_trading_enabled=paper_enabled,
                live_trading_enabled=live_enabled,
                broker_execution_enabled=broker_enabled,
                message=f"Alpaca account request failed with HTTP {account_response.status_code}: {detail}",
                warnings=warnings,
            )

        positions_response = requests.get(f"{endpoint}/v2/positions", headers=_headers(), timeout=10)
        orders_response = requests.get(
            f"{endpoint}/v2/orders",
            params={"status": "open", "limit": 50, "nested": "true"},
            headers=_headers(),
            timeout=10,
        )

        positions_payload = positions_response.json() if positions_response.status_code < 400 else []
        orders_payload = orders_response.json() if orders_response.status_code < 400 else []

        if not isinstance(positions_payload, list):
            positions_payload = []
        if not isinstance(orders_payload, list):
            orders_payload = []

        extra_warnings = list(warnings)
        if positions_response.status_code >= 400:
            extra_warnings.append(f"Positions request failed with HTTP {positions_response.status_code}.")
        if orders_response.status_code >= 400:
            extra_warnings.append(f"Open orders request failed with HTTP {orders_response.status_code}.")

        return AlpacaPaperSnapshot(
            status="connected",
            endpoint=endpoint,
            keys_configured=True,
            paper_trading_enabled=paper_enabled,
            live_trading_enabled=live_enabled,
            broker_execution_enabled=broker_enabled,
            account=_account(account_response.json()),
            positions=[_position(item) for item in positions_payload],
            open_orders=[_order(item) for item in orders_payload],
            message="Connected to Alpaca paper account.",
            warnings=extra_warnings,
        )
    except requests.RequestException as exc:
        return AlpacaPaperSnapshot(
            status="unavailable",
            endpoint=endpoint,
            keys_configured=True,
            paper_trading_enabled=paper_enabled,
            live_trading_enabled=live_enabled,
            broker_execution_enabled=broker_enabled,
            message=f"Alpaca paper account is unavailable: {exc}",
            warnings=warnings,
        )
    except ValueError as exc:
        return AlpacaPaperSnapshot(
            status="unavailable",
            endpoint=endpoint,
            keys_configured=True,
            paper_trading_enabled=paper_enabled,
            live_trading_enabled=live_enabled,
            broker_execution_enabled=broker_enabled,
            message=f"Alpaca returned an invalid response: {exc}",
            warnings=warnings,
        )
