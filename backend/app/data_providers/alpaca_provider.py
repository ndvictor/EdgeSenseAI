from __future__ import annotations

from typing import Any

import requests

from app.core.settings import settings
from app.data_providers.base import MarketCandle, MarketCandlesResponse, MarketSnapshot


class AlpacaProvider:
    """US equities snapshot via Alpaca Market Data API (aligned with other data_providers)."""

    default_symbols = ["AMD", "NVDA", "AAPL"]

    def __init__(self, timeout_seconds: int | None = None) -> None:
        self.api_key = settings.alpaca_api_key
        self.secret_key = settings.alpaca_secret_key
        self.base_url = (settings.alpaca_base_url or "https://data.alpaca.markets").rstrip("/")
        self.timeout_seconds = timeout_seconds or settings.market_data_provider_timeout_seconds

    def _require_config(self) -> None:
        if not settings.alpaca_market_data_enabled:
            raise ValueError("Alpaca market data is disabled (ALPACA_MARKET_DATA_ENABLED=false)")
        if not (self.api_key and str(self.api_key).strip() and self.secret_key and str(self.secret_key).strip()):
            raise ValueError("Alpaca is selected but ALPACA_API_KEY or ALPACA_SECRET_KEY is not set")

    @staticmethod
    def _num(value: Any) -> float | None:
        try:
            n = float(value)
        except (TypeError, ValueError):
            return None
        return n if n >= 0 else None

    def get_snapshot(self, symbol: str, asset_class: str = "stock") -> MarketSnapshot:
        self._require_config()
        if asset_class == "crypto" or "-USD" in symbol.upper():
            raise ValueError(
                "Model Lab Alpaca adapter supports US equities only; use yfinance or polygon for crypto symbols."
            )
        sym = symbol.upper().strip()
        r = requests.get(
            f"{self.base_url}/v2/stocks/{sym}/snapshot",
            headers={
                "APCA-API-KEY-ID": self.api_key,
                "APCA-API-SECRET-KEY": self.secret_key,
            },
            timeout=self.timeout_seconds,
        )
        r.raise_for_status()
        payload = r.json() or {}
        latest_trade = payload.get("latestTrade") or {}
        latest_quote = payload.get("latestQuote") or {}
        daily_bar = payload.get("dailyBar") or {}
        prev_daily_bar = payload.get("prevDailyBar") or {}

        current_price = self._num(latest_trade.get("p")) or self._num(daily_bar.get("c"))
        previous_close = self._num(prev_daily_bar.get("c"))
        if current_price is None:
            raise ValueError(f"Alpaca snapshot for {sym} did not include a trade or daily close")

        if previous_close is None:
            previous_close = current_price

        day_change_percent = ((current_price - previous_close) / previous_close * 100) if previous_close else 0.0

        volume = int(daily_bar.get("v") or 0)
        avg_vol = max(volume, 1)
        bid = self._num(latest_quote.get("bp")) or current_price
        ask = self._num(latest_quote.get("ap")) or current_price
        spread_percent = abs(ask - bid) / current_price * 100 if current_price else 0.0

        day_high = self._num(daily_bar.get("h")) or current_price
        day_low = self._num(daily_bar.get("l")) or current_price
        vwap = self._num(daily_bar.get("vw")) or (day_high + day_low + current_price) / 3
        volatility_proxy = min(0.9, max(0.05, abs(day_change_percent) / 100))

        return MarketSnapshot(
            symbol=sym,
            asset_class=asset_class,
            current_price=round(current_price, 4),
            previous_close=round(previous_close, 4),
            day_change_percent=round(day_change_percent, 4),
            volume=volume,
            relative_volume=round(volume / avg_vol, 2) if avg_vol else 1.0,
            bid=round(bid, 4),
            ask=round(ask, 4),
            spread_percent=round(spread_percent, 4),
            vwap=round(vwap, 4),
            volatility_proxy=round(volatility_proxy, 4),
            data_mode="alpaca_market_data",
        )

    def get_candles(self, symbol: str, period: str = "1mo", interval: str = "1d", asset_class: str = "stock") -> MarketCandlesResponse:
        from app.data_providers.yfinance_provider import YFinanceProvider

        return YFinanceProvider().get_candles(symbol, period, interval, asset_class)

    def get_watchlist_snapshots(self) -> list[MarketSnapshot]:
        snapshots: list[MarketSnapshot] = []
        for sym in self.default_symbols:
            try:
                snapshots.append(self.get_snapshot(sym, "stock"))
            except Exception:
                continue
        return snapshots
