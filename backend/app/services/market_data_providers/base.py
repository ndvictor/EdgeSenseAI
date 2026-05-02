from datetime import datetime
from typing import Any, Dict, List, Optional


MARKET_DATA_FIELDS = [
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
]


class MarketDataProvider:
    name = "base"

    def is_configured(self) -> bool:
        return True

    def get_snapshot(self, symbol: str) -> Dict[str, Any]:
        raise NotImplementedError

    def _response(
        self,
        symbol: str,
        data_quality: str,
        values: Optional[Dict[str, Any]] = None,
        unavailable_fields: Optional[List[str]] = None,
        not_configured_fields: Optional[List[str]] = None,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        values = values or {}
        unavailable = unavailable_fields if unavailable_fields is not None else [
            field for field in MARKET_DATA_FIELDS if values.get(field) is None
        ]
        not_configured = not_configured_fields if not_configured_fields is not None else []
        current_price = values.get("current_price")
        previous_close = values.get("previous_close")
        change = None
        if current_price is not None and previous_close is not None:
            change = current_price - previous_close

        return {
            "symbol": symbol.upper(),
            "current_price": current_price,
            "price": current_price,
            "previous_close": previous_close,
            "change": change,
            "change_percent": values.get("change_percent"),
            "day_high": values.get("day_high"),
            "day_low": values.get("day_low"),
            "volume": values.get("volume"),
            "average_volume": values.get("average_volume"),
            "bid": values.get("bid"),
            "ask": values.get("ask"),
            "bid_ask_spread": values.get("bid_ask_spread"),
            "market_cap": values.get("market_cap"),
            "fifty_two_week_high": values.get("fifty_two_week_high"),
            "fifty_two_week_low": values.get("fifty_two_week_low"),
            "sector": values.get("sector"),
            "industry": values.get("industry"),
            "source": self.name,
            "provider": self.name,
            "data_quality": data_quality,
            "is_mock": False,
            "unavailable_fields": unavailable,
            "not_configured_fields": not_configured,
            "timestamp": datetime.utcnow().isoformat(),
            "error": error,
            "source_fields_used": values.get("source_fields_used", {}),
        }

    def unavailable(self, symbol: str, error: Optional[str] = None) -> Dict[str, Any]:
        return self._response(
            symbol=symbol,
            data_quality="unavailable",
            unavailable_fields=MARKET_DATA_FIELDS.copy(),
            error=error,
        )

    def not_configured(self, symbol: str, reason: Optional[str] = None) -> Dict[str, Any]:
        return self._response(
            symbol=symbol,
            data_quality="not_configured",
            unavailable_fields=[],
            not_configured_fields=MARKET_DATA_FIELDS.copy(),
            error=reason,
        )
