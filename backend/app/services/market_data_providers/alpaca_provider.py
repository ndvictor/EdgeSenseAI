from typing import Any, Dict, Optional

import requests

from app.core.settings import settings
from app.services.market_data_providers.base import MARKET_DATA_FIELDS, MarketDataProvider


class AlpacaMarketDataProvider(MarketDataProvider):
    name = "alpaca"

    def __init__(
        self,
        enabled: Optional[bool] = None,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ) -> None:
        self.enabled = settings.alpaca_market_data_enabled if enabled is None else enabled
        self.api_key = settings.alpaca_api_key if api_key is None else api_key
        self.secret_key = settings.alpaca_secret_key if secret_key is None else secret_key
        self.base_url = (base_url or settings.alpaca_base_url or "https://data.alpaca.markets").rstrip("/")
        self.timeout_seconds = timeout_seconds or settings.market_data_provider_timeout_seconds

    def is_configured(self) -> bool:
        return bool(self.enabled and self.api_key and self.secret_key)

    def get_snapshot(self, symbol: str) -> Dict[str, Any]:
        if not self.enabled:
            return self.not_configured(symbol, reason="ALPACA_MARKET_DATA_ENABLED=false")
        if not self.api_key or not self.secret_key:
            return self.not_configured(symbol, reason="ALPACA_API_KEY or ALPACA_SECRET_KEY is missing")

        try:
            response = requests.get(
                f"{self.base_url}/v2/stocks/{symbol}/snapshot",
                headers={
                    "APCA-API-KEY-ID": self.api_key,
                    "APCA-API-SECRET-KEY": self.secret_key,
                },
                timeout=self.timeout_seconds,
            )
            if response.status_code >= 400:
                return self.unavailable(symbol, error=f"Alpaca HTTP {response.status_code}: {response.text[:160]}")

            payload = response.json()
            latest_trade = payload.get("latestTrade") or {}
            latest_quote = payload.get("latestQuote") or {}
            daily_bar = payload.get("dailyBar") or {}
            prev_daily_bar = payload.get("prevDailyBar") or {}

            current_price = self._number(latest_trade.get("p")) or self._number(daily_bar.get("c"))
            previous_close = self._number(prev_daily_bar.get("c"))
            day_high = self._number(daily_bar.get("h"))
            day_low = self._number(daily_bar.get("l"))
            volume = self._number(daily_bar.get("v"))
            bid = self._number(latest_quote.get("bp"))
            ask = self._number(latest_quote.get("ap"))

            change_percent = None
            if current_price is not None and previous_close:
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
                "bid": bid,
                "ask": ask,
                "bid_ask_spread": bid_ask_spread,
                "source_fields_used": {
                    "current_price": "latestTrade.p" if latest_trade.get("p") is not None else "dailyBar.c",
                    "previous_close": "prevDailyBar.c",
                    "bid": "latestQuote.bp",
                    "ask": "latestQuote.ap",
                },
            }
            if current_price is None:
                return self.unavailable(symbol, error="Alpaca snapshot did not include latest trade or daily close")

            return self._response(
                symbol=symbol,
                data_quality="real",
                values=values,
                unavailable_fields=[field for field in MARKET_DATA_FIELDS if values.get(field) is None],
            )
        except requests.RequestException as exc:
            return self.unavailable(symbol, error=str(exc))
        except ValueError as exc:
            return self.unavailable(symbol, error=f"Invalid Alpaca response: {exc}")

    def _number(self, value: Any) -> Optional[float]:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if number >= 0 else None
