from __future__ import annotations

from datetime import datetime, timedelta, timezone

import requests

from app.core.settings import settings
from app.data_providers.base import MarketCandle, MarketCandlesResponse, MarketSnapshot


class PolygonProvider:
    """Market data via Polygon.io snapshot + aggregates (aligned with YFinanceProvider interface)."""

    default_symbols = ["AMD", "NVDA", "BTC-USD"]
    BASE = "https://api.polygon.io"

    def __init__(self, timeout_seconds: int | None = None) -> None:
        self.api_key = settings.polygon_api_key
        self.timeout_seconds = timeout_seconds or settings.market_data_provider_timeout_seconds

    def _require_key(self) -> None:
        if not self.api_key or not str(self.api_key).strip():
            raise ValueError("Polygon is selected but POLYGON_API_KEY is not set")

    @staticmethod
    def _to_crypto_ticker(symbol: str) -> str:
        s = symbol.upper().strip().replace("-", "")
        if s.endswith("USD") and len(s) > 3:
            return f"X:{s[:-3]}USD"
        return symbol.upper().strip()

    def _snapshot(self, symbol: str, asset_class: str) -> dict:
        self._require_key()
        sym = symbol.upper().strip()
        is_crypto = asset_class == "crypto" or "-USD" in sym
        if is_crypto:
            url = f"{self.BASE}/v2/snapshot/locale/global/markets/crypto/tickers/{self._to_crypto_ticker(sym)}"
        else:
            url = f"{self.BASE}/v2/snapshot/locale/us/markets/stocks/tickers/{sym}"
        r = requests.get(url, params={"apiKey": self.api_key}, timeout=self.timeout_seconds)
        r.raise_for_status()
        return r.json() or {}

    def get_snapshot(self, symbol: str, asset_class: str = "stock") -> MarketSnapshot:
        payload = self._snapshot(symbol, asset_class)
        ticker = payload.get("ticker") or {}
        day = ticker.get("day") or {}
        prev = ticker.get("prevDay") or {}
        lt = ticker.get("lastTrade") or {}
        lq = ticker.get("lastQuote") or {}

        def num(v):  # noqa: ANN001
            try:
                return float(v) if v is not None else None
            except (TypeError, ValueError):
                return None

        current_price = num(lt.get("p")) or num(day.get("c")) or num(prev.get("c"))
        previous_close = num(prev.get("c")) or current_price or 0.0
        if current_price is None:
            raise ValueError(f"No Polygon price for {symbol}")

        day_change_percent = num(ticker.get("todaysChangePerc"))
        if day_change_percent is None and previous_close:
            day_change_percent = ((current_price - previous_close) / previous_close) * 100

        volume = int(day.get("v") or 0)
        avg_vol = volume or 1
        bid = num(lq.get("p")) or num(lq.get("bp")) or current_price
        ask = num(lq.get("P")) or num(lq.get("ap")) or current_price
        spread_percent = abs(ask - bid) / current_price * 100 if current_price else 0.0
        vwap = num(day.get("vw")) or current_price
        volatility_proxy = min(0.9, max(0.05, abs(day_change_percent or 0) / 100))

        return MarketSnapshot(
            symbol=symbol.upper().strip(),
            asset_class=asset_class,
            current_price=round(current_price, 4),
            previous_close=round(previous_close, 4),
            day_change_percent=round(day_change_percent or 0.0, 4),
            volume=volume,
            relative_volume=round(volume / avg_vol, 2) if avg_vol else 1.0,
            bid=round(bid, 4),
            ask=round(ask, 4),
            spread_percent=round(spread_percent, 4),
            vwap=round(vwap, 4),
            volatility_proxy=round(volatility_proxy, 4),
            data_mode="polygon_io",
        )

    def get_candles(self, symbol: str, period: str = "1mo", interval: str = "1d", asset_class: str = "stock") -> MarketCandlesResponse:
        self._require_key()
        sym = symbol.upper().strip()
        is_crypto = asset_class == "crypto" or "-USD" in sym
        ticker_path = self._to_crypto_ticker(sym) if is_crypto else sym

        end = datetime.now(timezone.utc).date()
        days_map = {"1d": 2, "5d": 7, "1mo": 35, "3mo": 98, "6mo": 190, "1y": 370}
        days = days_map.get(period.lower().strip(), 35)
        start = end - timedelta(days=days)

        mult = 1
        span = "day"
        il = interval.lower().strip()
        if il.endswith("h") and il[:-1].isdigit():
            span = "hour"
            mult = max(1, int(il[:-1]))

        url = f"{self.BASE}/v2/aggs/ticker/{ticker_path}/range/{mult}/{span}/{start}/{end}"
        r = requests.get(
            url,
            params={"apiKey": self.api_key, "sort": "asc", "limit": 50000},
            timeout=self.timeout_seconds,
        )
        r.raise_for_status()
        payload = r.json() or {}
        results = payload.get("results") or []
        candles: list[MarketCandle] = []
        for bar in results:
            ts = bar.get("t")
            tstr = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat() if ts else ""
            candles.append(
                MarketCandle(
                    time=tstr,
                    open=round(float(bar.get("o")), 4),
                    high=round(float(bar.get("h")), 4),
                    low=round(float(bar.get("l")), 4),
                    close=round(float(bar.get("c")), 4),
                    volume=int(bar.get("v") or 0),
                )
            )
        return MarketCandlesResponse(
            symbol=sym,
            asset_class=asset_class,
            interval=interval,
            period=period,
            data_mode="polygon_io",
            candles=candles,
        )

    def get_watchlist_snapshots(self) -> list[MarketSnapshot]:
        snapshots: list[MarketSnapshot] = []
        for symbol in self.default_symbols:
            asset_class = "crypto" if "-USD" in symbol else "stock"
            try:
                snapshots.append(self.get_snapshot(symbol, asset_class))
            except Exception:
                continue
        return snapshots
