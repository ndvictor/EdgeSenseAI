from typing import Any, Dict, Optional

import yfinance as yf

from app.core.settings import settings
from app.services.market_data_providers.alpaca_provider import AlpacaMarketDataProvider
from app.services.market_data_providers.yfinance_provider import YFinanceMarketDataProvider


class MarketDataService:
    """Read-only market data service using configured provider priority."""

    def __init__(self, provider_priority: Optional[list[str]] = None, providers: Optional[Dict[str, Any]] = None):
        self.provider_priority = provider_priority or settings.market_data_provider_priority
        self.providers = providers or {
            "alpaca": AlpacaMarketDataProvider(),
            "yfinance": YFinanceMarketDataProvider(),
        }

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        snapshot = self.get_market_snapshot(symbol)
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
            "is_mock": False,
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

    def get_price_history(self, symbol: str, period: str = "6mo", interval: str = "1d") -> Dict[str, Any]:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval)
            if hist.empty:
                return self._get_unavailable_history(symbol, period, interval, error="No data returned")

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
        except Exception as exc:
            return self._get_unavailable_history(symbol, period, interval, error=str(exc))

    def get_market_snapshot(self, symbol: str) -> Dict[str, Any]:
        provider_statuses = []

        for provider_name in self.provider_priority:
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

            if snapshot.get("data_quality") == "real" and snapshot.get("price") is not None:
                snapshot["provider_statuses"] = provider_statuses
                return snapshot

        final_error = "; ".join(
            f"{status['provider']}: {status.get('data_quality')} {status.get('error') or ''}".strip()
            for status in provider_statuses
        )
        snapshot = self._get_unavailable_snapshot(symbol, error=final_error or "No provider returned market data")
        snapshot["provider_statuses"] = provider_statuses
        return snapshot

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
