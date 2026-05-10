from __future__ import annotations

import os
from datetime import datetime, time, timedelta, timezone
from typing import Any, Literal
from zoneinfo import ZoneInfo

import requests
from pydantic import BaseModel, Field

from app.core.settings import settings


MarketSession = Literal["pre_market", "regular_market", "post_market", "closed"]
ClockSource = Literal["alpaca_clock", "fallback_timezone"]

ET_TZ = ZoneInfo("America/New_York")
UTC_TZ = ZoneInfo("UTC")


class MarketSessionState(BaseModel):
    market_session: MarketSession
    market_date: str
    current_time_et: str
    clock_source: ClockSource
    is_trading_day: bool
    is_market_open: bool
    is_pre_market: bool
    is_regular_market: bool
    is_post_market: bool
    next_open: str | None = None
    next_close: str | None = None
    warnings: list[str] = Field(default_factory=list)


def _alpaca_key_id() -> str:
    return (
        os.getenv("ALPACA_API_KEY_ID")
        or os.getenv("ALPACA_API_KEY")
        or os.getenv("APCA_API_KEY_ID")
        or settings.alpaca_api_key
        or ""
    )


def _alpaca_secret_key() -> str:
    return (
        os.getenv("ALPACA_API_SECRET_KEY")
        or os.getenv("ALPACA_SECRET_KEY")
        or os.getenv("APCA_API_SECRET_KEY")
        or settings.alpaca_secret_key
        or ""
    )


def _paper_base_url() -> str:
    return (
        os.getenv("ALPACA_PAPER_TRADING_BASE_URL")
        or os.getenv("APCA_API_BASE_URL")
        or "https://paper-api.alpaca.markets"
    ).rstrip("/")


def _headers() -> dict[str, str]:
    return {"APCA-API-KEY-ID": _alpaca_key_id(), "APCA-API-SECRET-KEY": _alpaca_secret_key()}


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        raw = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC_TZ)
        return dt
    except Exception:
        return None


def _now_et(now: datetime | None = None) -> datetime:
    dt = now or datetime.now(tz=UTC_TZ)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC_TZ)
    return dt.astimezone(ET_TZ)


def _is_weekday_trading_day(dt_et: datetime) -> bool:
    return dt_et.weekday() < 5


def _next_weekday_at(dt_et: datetime, target: time) -> datetime:
    candidate = datetime.combine(dt_et.date(), target, tzinfo=ET_TZ)
    if candidate <= dt_et:
        candidate += timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return candidate


def _fallback_session(dt_et: datetime, warnings: list[str] | None = None) -> MarketSessionState:
    warnings = list(warnings or [])
    market_date = dt_et.date().isoformat()
    trading_day = _is_weekday_trading_day(dt_et)
    pre_start = time(4, 0)
    regular_start = time(9, 30)
    regular_end = time(16, 0)
    post_end = time(20, 0)
    t = dt_et.time()

    if not trading_day:
        session: MarketSession = "closed"
    elif pre_start <= t < regular_start:
        session = "pre_market"
    elif regular_start <= t < regular_end:
        session = "regular_market"
    elif regular_end <= t < post_end:
        session = "post_market"
    else:
        session = "closed"

    next_open = _next_weekday_at(dt_et, regular_start)
    next_close = datetime.combine(dt_et.date(), regular_end, tzinfo=ET_TZ)
    if next_close <= dt_et or not trading_day:
        next_close = _next_weekday_at(dt_et, regular_end)

    return MarketSessionState(
        market_session=session,
        market_date=market_date,
        current_time_et=dt_et.isoformat(),
        clock_source="fallback_timezone",
        is_trading_day=trading_day,
        is_market_open=session == "regular_market",
        is_pre_market=session == "pre_market",
        is_regular_market=session == "regular_market",
        is_post_market=session == "post_market",
        next_open=next_open.isoformat(),
        next_close=next_close.isoformat(),
        warnings=warnings,
    )


def _alpaca_session() -> MarketSessionState | None:
    if not (_alpaca_key_id() and _alpaca_secret_key()):
        return None
    try:
        response = requests.get(f"{_paper_base_url()}/v2/clock", headers=_headers(), timeout=8)
        if response.status_code >= 400:
            return None
        payload = response.json()
    except Exception:
        return None

    timestamp = _parse_dt(payload.get("timestamp")) or datetime.now(tz=UTC_TZ)
    dt_et = timestamp.astimezone(ET_TZ)
    fallback = _fallback_session(dt_et)
    is_open = bool(payload.get("is_open"))
    next_open = _parse_dt(payload.get("next_open"))
    next_close = _parse_dt(payload.get("next_close"))
    if is_open:
        session: MarketSession = "regular_market"
    else:
        session = fallback.market_session

    return MarketSessionState(
        market_session=session,
        market_date=dt_et.date().isoformat(),
        current_time_et=dt_et.isoformat(),
        clock_source="alpaca_clock",
        is_trading_day=fallback.is_trading_day or is_open,
        is_market_open=is_open,
        is_pre_market=session == "pre_market",
        is_regular_market=session == "regular_market",
        is_post_market=session == "post_market",
        next_open=next_open.astimezone(ET_TZ).isoformat() if next_open else fallback.next_open,
        next_close=next_close.astimezone(ET_TZ).isoformat() if next_close else fallback.next_close,
        warnings=[] if is_open or fallback.is_trading_day else ["alpaca_clock_market_closed"],
    )


def get_market_session_state(now: datetime | None = None, *, prefer_alpaca: bool = True) -> MarketSessionState:
    if prefer_alpaca and now is None:
        state = _alpaca_session()
        if state is not None:
            return state
    warnings = [] if now is not None else ["alpaca_clock_unavailable_using_timezone_fallback"]
    return _fallback_session(_now_et(now), warnings=warnings)


def scanner_mode_for_session(state: MarketSessionState) -> str:
    if state.market_session == "pre_market":
        return "pre_market"
    if state.market_session == "regular_market":
        return "regular_market"
    if state.market_session == "post_market":
        return "post_market"
    return "market_closed"
