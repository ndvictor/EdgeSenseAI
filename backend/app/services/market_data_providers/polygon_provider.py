"""Polygon.io snapshot quotes for REST /market-data routes."""

from __future__ import annotations

from typing import Any, Optional

import requests

from app.core.settings import settings
from app.services.market_data_providers.base import MARKET_DATA_FIELDS, MarketDataProvider


class PolygonMarketDataProvider(MarketDataProvider):
    name = "polygon"
    BASE = "https://api.polygon.io"

    def __init__(self, api_key: Optional[str] = None, timeout_seconds: Optional[int] = None) -> None:
        self.api_key = settings.polygon_api_key if api_key is None else api_key
        self.timeout_seconds = timeout_seconds or settings.market_data_provider_timeout_seconds

    def is_configured(self) -> bool:
        return bool(self.api_key and str(self.api_key).strip())

    def _stock_snapshot_url(self, symbol: str) -> str:
        return f"{self.BASE}/v2/snapshot/locale/us/markets/stocks/tickers/{symbol.upper().strip()}"

    def _crypto_snapshot_url(self, polygon_ticker: str) -> str:
        return f"{self.BASE}/v2/snapshot/locale/global/markets/crypto/tickers/{polygon_ticker}"

    @staticmethod
    def _to_crypto_ticker(symbol: str) -> str:
        s = symbol.upper().strip().replace("-", "")
        if s.endswith("USD") and len(s) > 3:
            return f"X:{s[:-3]}USD"
        return symbol.upper().strip()

    def get_snapshot(self, symbol: str) -> dict[str, Any]:
        if not self.is_configured():
            return self.not_configured(symbol, reason="POLYGON_API_KEY is missing")

        sym = symbol.upper().strip()
        is_crypto = "-USD" in sym
        url = self._crypto_snapshot_url(self._to_crypto_ticker(sym)) if is_crypto else self._stock_snapshot_url(sym)

        try:
            response = requests.get(url, params={"apiKey": self.api_key}, timeout=self.timeout_seconds)
            if response.status_code == 404:
                return self.unavailable(symbol, error="Polygon returned 404 (unknown ticker for this asset class)")
            if response.status_code >= 400:
                return self.unavailable(symbol, error=f"Polygon HTTP {response.status_code}: {response.text[:200]}")

            payload = response.json() or {}
            if (payload.get("status") or "").upper() not in {"", "OK"} and "ticker" not in payload:
                return self.unavailable(symbol, error=str(payload.get("error") or payload.get("message") or payload))

            ticker = payload.get("ticker") or {}
            day = ticker.get("day") or {}
            prev = ticker.get("prevDay") or {}
            lt = ticker.get("lastTrade") or {}
            lq = ticker.get("lastQuote") or {}

            current_price = self._number(lt.get("p")) or self._number(day.get("c")) or self._number(prev.get("c"))
            previous_close = self._number(prev.get("c"))
            day_high = self._number(day.get("h"))
            day_low = self._number(day.get("l"))
            volume = self._number(day.get("v"))
            vwap = self._number(day.get("vw"))

            bid = self._number(lq.get("p"))
            ask = self._number(lq.get("P"))
            if bid is None:
                bid = self._number(lq.get("bp"))
            if ask is None:
                ask = self._number(lq.get("ap"))

            change_percent = self._number(ticker.get("todaysChangePerc"))
            if change_percent is None and current_price is not None and previous_close:
                change_percent = ((current_price - previous_close) / previous_close) * 100

            bid_ask_spread = None
            if bid is not None and ask is not None and (bid + ask) > 0:
                bid_ask_spread = ((ask - bid) / ((bid + ask) / 2)) * 100

            values = {
                "current_price": current_price,
                "previous_close": previous_close,
                "change_percent": change_percent,
                "day_high": day_high,
                "day_low": day_low,
                "volume": volume,
                "average_volume": volume,
                "bid": bid,
                "ask": ask,
                "bid_ask_spread": bid_ask_spread,
                "source_fields_used": {
                    "current_price": "lastTrade.p" if lt.get("p") is not None else "day.c",
                    "previous_close": "prevDay.c",
                },
            }

            if current_price is None:
                return self.unavailable(symbol, error="Polygon snapshot had no trade, day close, or previous close")

            return self._response(
                symbol=sym,
                data_quality="real",
                values=values,
                unavailable_fields=[field for field in MARKET_DATA_FIELDS if values.get(field) is None],
            )
        except requests.RequestException as exc:
            return self.unavailable(symbol, error=str(exc))

    def _number(self, value: Any) -> Optional[float]:
        try:
            if value is None:
                return None
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number
