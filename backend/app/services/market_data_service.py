from typing import Any, Dict, Optional

import requests
import yfinance as yf

from app.core.settings import settings
from app.services.market_data_providers.alpaca_provider import AlpacaMarketDataProvider
from app.services.market_data_providers.mock_provider import MockMarketDataProvider
from app.services.market_data_providers.yfinance_provider import YFinanceMarketDataProvider


class MarketDataService:
    """Read-only market data service using configured provider priority.

    Important product rule:
    - source=mock is allowed for explicit UI/testing workflows.
    - source=auto must never silently fall back to mock, because that can make fake data look real.
    """

    def __init__(self, provider_priority: Optional[list[str]] = None, providers: Optional[Dict[str, Any]] = None):
        self.provider_priority = provider_priority or settings.market_data_provider_priority
        self.providers = providers or {
            "alpaca": AlpacaMarketDataProvider(),
            "yfinance": YFinanceMarketDataProvider(),
            "mock": MockMarketDataProvider(),
        }

    def _priority_for_source(self, source: str | None = None) -> list[str]:
        if not source or source == "auto":
            return [provider for provider in self.provider_priority if provider != "mock"]
        return [source.lower().strip()]

    def get_quote(self, symbol: str, source: str | None = None) -> Dict[str, Any]:
        snapshot = self.get_market_snapshot(symbol, source=source)
        if snapshot.get("data_quality") in {"unavailable", "not_configured"}:
            return self._get_unavailable_quote(symbol, error=snapshot.get("error"))
        return {
            "symbol": symbol.upper(),
            "price": snapshot.get("price"),
            "previous_close": snapshot.get("previous_close"),
            "change": snapshot.get("change"),
            "change_percent": snapshot.get("change_percent"),
            "day_high": snapshot.get("day_high"),
            "day_low": snapshot.get("day_low"),
            "volume": snapshot.get("volume"),
            "provider": snapshot.get("provider"),
            "source": snapshot.get("source"),
            "is_mock": snapshot.get("is_mock", False),
            "data_quality": snapshot.get("data_quality"),
            "unavailable_fields": snapshot.get("unavailable_fields", []),
            "not_configured_fields": snapshot.get("not_configured_fields", []),
        }

    def get_profile(self, symbol: str) -> Dict[str, Any]:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}
            return {
                "symbol": symbol.upper(),
                "name": info.get("longName") or info.get("shortName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "market_cap": info.get("marketCap"),
                "description": info.get("longBusinessSummary"),
                "website": info.get("website"),
                "provider": "yfinance",
                "is_mock": False,
            }
        except Exception as exc:
            return self._get_unavailable_profile(symbol, error=str(exc))

    def get_price_history(self, symbol: str, period: str = "6mo", interval: str = "1d", source: str | None = None) -> Dict[str, Any]:
        requested_source = (source or "auto").lower().strip()
        if requested_source == "mock":
            return self._get_mock_history(symbol, period, interval)

        yfinance_error = None
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval)
            if not hist.empty:
                data = []
                for date, row in hist.iterrows():
                    data.append({
                        "date": date.isoformat(),
                        "open": float(row["Open"]) if row["Open"] else None,
                        "high": float(row["High"]) if row["High"] else None,
                        "low": float(row["Low"]) if row["Low"] else None,
                        "close": float(row["Close"]) if row["Close"] else None,
                        "volume": int(row["Volume"]) if row["Volume"] else None,
                    })
                return {
                    "symbol": symbol.upper(),
                    "period": period,
                    "interval": interval,
                    "data": data,
                    "provider": "yfinance",
                    "is_mock": False,
                    "data_quality": "real",
                }
            yfinance_error = f"No data returned from {requested_source} source"
        except Exception as exc:
            yfinance_error = str(exc)

        yahoo_fallback = self._get_history_from_yahoo_chart_api(symbol, period, interval)
        if yahoo_fallback.get("data"):
            return yahoo_fallback

        combined_error = yfinance_error or yahoo_fallback.get("error") or "No market history returned"
        if yahoo_fallback.get("error"):
            combined_error = f"{combined_error}; Yahoo chart fallback: {yahoo_fallback.get('error')}"
        return self._get_unavailable_history(symbol, period, interval, error=combined_error)

    def _get_history_from_yahoo_chart_api(self, symbol: str, period: str, interval: str) -> Dict[str, Any]:
        try:
            response = requests.get(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol.upper()}",
                params={"range": period, "interval": interval},
                headers={"User-Agent": "Mozilla/5.0 EdgeSenseAI/0.8", "Accept": "application/json,text/plain,*/*"},
                timeout=10,
            )
            if response.status_code >= 400:
                return self._get_unavailable_history(symbol, period, interval, error=f"Yahoo chart API HTTP {response.status_code}")
            payload = response.json()
            result = (payload.get("chart", {}).get("result") or [None])[0]
            if not result:
                return self._get_unavailable_history(symbol, period, interval, error="Yahoo chart API returned no result")
            timestamps = result.get("timestamp") or []
            quote = ((result.get("indicators", {}) or {}).get("quote") or [{}])[0]
            opens = quote.get("open") or []
            highs = quote.get("high") or []
            lows = quote.get("low") or []
            closes = quote.get("close") or []
            volumes = quote.get("volume") or []
            data = []
            for idx, timestamp in enumerate(timestamps):
                close = self._number(closes[idx] if idx < len(closes) else None)
                if close is None:
                    continue
                data.append({
                    "date": self._timestamp_to_iso(timestamp),
                    "open": self._number(opens[idx] if idx < len(opens) else None),
                    "high": self._number(highs[idx] if idx < len(highs) else None),
                    "low": self._number(lows[idx] if idx < len(lows) else None),
                    "close": close,
                    "volume": int(volumes[idx]) if idx < len(volumes) and volumes[idx] is not None else None,
                })
            if not data:
                return self._get_unavailable_history(symbol, period, interval, error="Yahoo chart API returned no usable candles")
            return {
                "symbol": symbol.upper(),
                "period": period,
                "interval": interval,
                "data": data,
                "provider": "yahoo_chart_api",
                "is_mock": False,
                "data_quality": "real",
            }
        except Exception as exc:
            return self._get_unavailable_history(symbol, period, interval, error=str(exc))

    def get_market_snapshot(self, symbol: str, source: str | None = None) -> Dict[str, Any]:
        provider_statuses = []

        for provider_name in self._priority_for_source(source):
            provider = self.providers.get(provider_name)
            if provider is None:
                provider_statuses.append({"provider": provider_name, "data_quality": "not_configured", "error": "Provider is not registered"})
                continue

            snapshot = provider.get_snapshot(symbol.upper())
            provider_statuses.append({
                "provider": provider_name,
                "data_quality": snapshot.get("data_quality"),
                "error": snapshot.get("error"),
                "unavailable_fields": snapshot.get("unavailable_fields", []),
                "not_configured_fields": snapshot.get("not_configured_fields", []),
            })

            if snapshot.get("price") is not None and snapshot.get("data_quality") not in {"unavailable", "not_configured"}:
                snapshot["provider_statuses"] = provider_statuses
                return snapshot

        final_error = "; ".join(
            f"{status['provider']}: {status.get('data_quality')} {status.get('error') or ''}".strip()
            for status in provider_statuses
        )
        snapshot = self._get_unavailable_snapshot(symbol, error=final_error or "No configured real provider returned market data")
        snapshot["provider_statuses"] = provider_statuses
        return snapshot

    def _get_mock_history(self, symbol: str, period: str, interval: str, data_quality: str = "mock", error: str | None = None) -> Dict[str, Any]:
        snapshot = self.providers["mock"].get_snapshot(symbol)
        start = float(snapshot.get("price") or 100.0)
        data = []
        for i in range(30):
            close = start * (0.94 + i * 0.004)
            data.append({
                "date": f"2026-01-{i + 1:02d}T00:00:00",
                "open": round(close * 0.995, 4),
                "high": round(close * 1.012, 4),
                "low": round(close * 0.988, 4),
                "close": round(close, 4),
                "volume": int((snapshot.get("volume") or 1000000) * (0.7 + i * 0.01)),
            })
        return {
            "symbol": symbol.upper(),
            "period": period,
            "interval": interval,
            "data": data,
            "provider": "mock",
            "is_mock": True,
            "data_quality": data_quality,
            "error": error,
        }

    def _timestamp_to_iso(self, timestamp: int) -> str:
        from datetime import datetime, timezone

        return datetime.fromtimestamp(int(timestamp), tz=timezone.utc).isoformat()

    def _number(self, value: Any) -> Optional[float]:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if number >= 0 else None

    def _get_unavailable_quote(self, symbol: str, error: str | None = None) -> Dict[str, Any]:
        return {
            "symbol": symbol.upper(),
            "price": None,
            "previous_close": None,
            "change": None,
            "change_percent": None,
            "day_high": None,
            "day_low": None,
            "volume": None,
            "provider": None,
            "source": None,
            "is_mock": False,
            "data_quality": "unavailable",
            "error": error,
        }

    def _get_unavailable_profile(self, symbol: str, error: str | None = None) -> Dict[str, Any]:
        return {
            "symbol": symbol.upper(),
            "name": None,
            "sector": None,
            "industry": None,
            "market_cap": None,
            "description": None,
            "website": None,
            "provider": None,
            "is_mock": False,
            "data_quality": "unavailable",
            "error": error,
        }

    def _get_unavailable_history(self, symbol: str, period: str, interval: str, error: str | None = None) -> Dict[str, Any]:
        return {
            "symbol": symbol.upper(),
            "period": period,
            "interval": interval,
            "data": [],
            "provider": None,
            "is_mock": False,
            "data_quality": "unavailable",
            "error": error,
        }

    def _get_unavailable_snapshot(self, symbol: str, error: str | None = None) -> Dict[str, Any]:
        return {
            "symbol": symbol.upper(),
            "price": None,
            "previous_close": None,
            "change": None,
            "change_percent": None,
            "day_high": None,
            "day_low": None,
            "volume": None,
            "market_cap": None,
            "fifty_two_week_high": None,
            "fifty_two_week_low": None,
            "sector": None,
            "industry": None,
            "provider": None,
            "source": None,
            "is_mock": False,
            "data_quality": "unavailable",
            "source_fields_used": {"price_source": None, "previous_close_source": None},
            "unavailable_fields": [
                "current_price",
                "previous_close",
                "change_percent",
                "day_high",
                "day_low",
                "volume",
                "average_volume",
                "bid",
                "ask",
                "bid_ask_spread",
            ],
            "not_configured_fields": [],
            "error": error,
        }
