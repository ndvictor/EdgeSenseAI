from datetime import datetime, timezone
from time import sleep, time
from typing import Any, Dict, Optional

import requests
import yfinance as yf

from app.services.market_data_providers.base import MARKET_DATA_FIELDS, MarketDataProvider


class YFinanceMarketDataProvider(MarketDataProvider):
    name = "yfinance"
    _last_request_time: float = 0.0
    _min_request_interval: float = 0.3  # 300ms between requests to avoid 429

    def get_snapshot(self, symbol: str) -> Dict[str, Any]:
        errors: list[str] = []
        snapshot = self._get_snapshot_from_yfinance_library(symbol, errors)
        if snapshot.get("data_quality") == "real" and snapshot.get("price") is not None:
            return snapshot

        fallback_snapshot = self._get_snapshot_from_yahoo_chart_api(symbol, errors)
        if fallback_snapshot.get("data_quality") == "real" and fallback_snapshot.get("price") is not None:
            return fallback_snapshot

        return self.unavailable(symbol, error="; ".join(errors) or "No data returned from yfinance or Yahoo chart fallback")

    def _throttle(self) -> None:
        """Add small delay between requests to respect Yahoo Finance rate limits."""
        elapsed = time() - self._last_request_time
        if elapsed < self._min_request_interval:
            sleep(self._min_request_interval - elapsed)
        self._last_request_time = time()

    def _get_snapshot_from_yfinance_library(self, symbol: str, errors: list[str]) -> Dict[str, Any]:
        try:
            self._throttle()
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d", interval="1d")
            info = ticker.info or {}
            fast = getattr(ticker, "fast_info", {}) or {}

            if hist.empty:
                errors.append("yfinance library returned empty history")
                return self.unavailable(symbol, error="yfinance library returned empty history")

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
                    "current_price": "yfinance.fast_info.last_price/info.currentPrice/history.Close[-1]",
                    "previous_close": "yfinance.fast_info.previous_close/info.previousClose/history.Close[-2]",
                    "bid": "yfinance.info.bid/fast_info.bid",
                    "ask": "yfinance.info.ask/fast_info.ask",
                },
            }
            if current_price is None:
                errors.append("yfinance library did not return current price")
                return self.unavailable(symbol, error="yfinance library did not return current price")

            return self._response(
                symbol=symbol,
                data_quality="real",
                values=values,
                unavailable_fields=[field for field in MARKET_DATA_FIELDS if values.get(field) is None],
            )
        except Exception as exc:
            errors.append(f"yfinance library error: {str(exc)}")
            return self.unavailable(symbol, error=str(exc))

    def _get_snapshot_from_yahoo_chart_api(self, symbol: str, errors: list[str]) -> Dict[str, Any]:
        try:
            self._throttle()
            response = requests.get(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol.upper()}",
                params={"range": "5d", "interval": "1d"},
                headers={
                    "User-Agent": "Mozilla/5.0 EdgeSenseAI/0.8",
                    "Accept": "application/json,text/plain,*/*",
                },
                timeout=10,
            )
            if response.status_code >= 400:
                errors.append(f"Yahoo chart API HTTP {response.status_code}")
                return self.unavailable(symbol, error=f"Yahoo chart API HTTP {response.status_code}")
            payload = response.json()
            result = (payload.get("chart", {}).get("result") or [None])[0]
            if not result:
                errors.append("Yahoo chart API returned no result")
                return self.unavailable(symbol, error="Yahoo chart API returned no result")

            meta = result.get("meta", {})
            quote = ((result.get("indicators", {}) or {}).get("quote") or [{}])[0]
            closes = [self._number(value) for value in quote.get("close", [])]
            highs = [self._number(value) for value in quote.get("high", [])]
            lows = [self._number(value) for value in quote.get("low", [])]
            volumes = [self._number(value) for value in quote.get("volume", [])]
            closes = [value for value in closes if value is not None]
            highs = [value for value in highs if value is not None]
            lows = [value for value in lows if value is not None]
            volumes = [value for value in volumes if value is not None]
            if not closes:
                errors.append("Yahoo chart API returned no close prices")
                return self.unavailable(symbol, error="Yahoo chart API returned no close prices")

            current_price = self._number(meta.get("regularMarketPrice")) or closes[-1]
            previous_close = self._number(meta.get("chartPreviousClose")) or (closes[-2] if len(closes) > 1 else closes[-1])
            volume = volumes[-1] if volumes else None
            average_volume = sum(volumes) / len(volumes) if volumes else None
            bid = self._number(meta.get("bid"))
            ask = self._number(meta.get("ask"))
            day_high = highs[-1] if highs else None
            day_low = lows[-1] if lows else None

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
                "market_cap": None,
                "fifty_two_week_high": self._number(meta.get("fiftyTwoWeekHigh")),
                "fifty_two_week_low": self._number(meta.get("fiftyTwoWeekLow")),
                "sector": None,
                "industry": None,
                "source_fields_used": {
                    "current_price": "yahoo_chart.meta.regularMarketPrice/quote.close[-1]",
                    "previous_close": "yahoo_chart.meta.chartPreviousClose/quote.close[-2]",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            }
            return self._response(
                symbol=symbol,
                data_quality="real",
                values=values,
                unavailable_fields=[field for field in MARKET_DATA_FIELDS if values.get(field) is None],
            )
        except Exception as exc:
            errors.append(f"Yahoo chart API fallback error: {str(exc)}")
            return self.unavailable(symbol, error=str(exc))

    def _number(self, value: Any) -> Optional[float]:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if number >= 0 else None
