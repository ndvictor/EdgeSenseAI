from typing import Any, Dict, Optional

import yfinance as yf

from app.services.market_data_providers.base import MARKET_DATA_FIELDS, MarketDataProvider


class YFinanceMarketDataProvider(MarketDataProvider):
    name = "yfinance"

    def get_snapshot(self, symbol: str) -> Dict[str, Any]:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d", interval="1d")
            info = ticker.info or {}
            fast = getattr(ticker, "fast_info", {}) or {}

            if hist.empty:
                return self.unavailable(symbol, error="No data returned from yfinance")

            current_price = self._number(fast.get("last_price")) or self._number(info.get("currentPrice")) or self._number(hist["Close"].iloc[-1])
            previous_close = self._number(fast.get("previous_close")) or self._number(info.get("previousClose"))
            if previous_close is None and len(hist) > 1:
                previous_close = self._number(hist["Close"].iloc[-2])

            day_high = self._number(info.get("dayHigh")) or self._number(hist["High"].iloc[-1])
            day_low = self._number(info.get("dayLow")) or self._number(hist["Low"].iloc[-1])
            volume = self._number(info.get("volume")) or self._number(hist["Volume"].iloc[-1])
            average_volume = self._number(info.get("averageVolume")) or self._number(hist["Volume"].tail(5).mean())
            bid = self._number(info.get("bid")) or self._number(fast.get("bid"))
            ask = self._number(info.get("ask")) or self._number(fast.get("ask"))

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
                "average_volume": average_volume,
                "bid": bid,
                "ask": ask,
                "bid_ask_spread": bid_ask_spread,
                "market_cap": self._number(info.get("marketCap")),
                "fifty_two_week_high": self._number(info.get("fiftyTwoWeekHigh")),
                "fifty_two_week_low": self._number(info.get("fiftyTwoWeekLow")),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "source_fields_used": {
                    "current_price": "fast_info.last_price/info.currentPrice/history.Close[-1]",
                    "previous_close": "fast_info.previous_close/info.previousClose/history.Close[-2]",
                    "bid": "info.bid/fast_info.bid",
                    "ask": "info.ask/fast_info.ask",
                },
            }
            if current_price is None:
                return self.unavailable(symbol, error="yfinance did not return a current price")

            return self._response(
                symbol=symbol,
                data_quality="real",
                values=values,
                unavailable_fields=[field for field in MARKET_DATA_FIELDS if values.get(field) is None],
            )
        except Exception as exc:
            return self.unavailable(symbol, error=str(exc))

    def _number(self, value: Any) -> Optional[float]:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if number >= 0 else None
