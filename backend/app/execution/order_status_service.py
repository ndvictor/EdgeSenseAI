"""Fetch / cancel / sync Alpaca orders (paper endpoint by default)."""

from __future__ import annotations

import os
from typing import Any

import requests


def _headers() -> dict[str, str]:
    key = os.getenv("ALPACA_API_KEY_ID") or os.getenv("ALPACA_API_KEY") or ""
    sec = os.getenv("ALPACA_API_SECRET_KEY") or os.getenv("ALPACA_SECRET_KEY") or ""
    return {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec}


def _paper_base() -> str:
    return (
        os.getenv("ALPACA_PAPER_TRADING_BASE_URL")
        or os.getenv("APCA_API_BASE_URL")
        or "https://paper-api.alpaca.markets"
    ).rstrip("/")


def get_broker_order(order_id: str, *, paper: bool = True) -> dict[str, Any]:
    base = _paper_base() if paper else (os.getenv("ALPACA_LIVE_TRADING_BASE_URL") or "https://api.alpaca.markets").rstrip("/")
    try:
        r = requests.get(f"{base}/v2/orders/{order_id}", headers=_headers(), timeout=15)
        if r.status_code >= 400:
            return {"ok": False, "status_code": r.status_code, "body": r.text[:300]}
        return {"ok": True, "order": r.json()}
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc)[:200]}


def cancel_broker_order(order_id: str, *, paper: bool = True) -> dict[str, Any]:
    base = _paper_base() if paper else (os.getenv("ALPACA_LIVE_TRADING_BASE_URL") or "https://api.alpaca.markets").rstrip("/")
    try:
        r = requests.delete(f"{base}/v2/orders/{order_id}", headers=_headers(), timeout=15)
        if r.status_code >= 400:
            return {"ok": False, "status_code": r.status_code, "body": r.text[:300]}
        try:
            body = r.json()
        except Exception:
            body = {"text": r.text[:200]}
        return {"ok": True, "result": body}
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc)[:200]}
