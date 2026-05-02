from typing import Any, Dict

from app.services.market_data_providers.base import MARKET_DATA_FIELDS, MarketDataProvider


class MockMarketDataProvider(MarketDataProvider):
    name = "mock"

    snapshots = {
        "AMD": {
            "current_price": 162.40,
            "previous_close": 158.90,
            "change_percent": 2.20,
            "day_high": 164.10,
            "day_low": 158.70,
            "volume": 68420000,
            "average_volume": 43000000,
            "bid": 162.35,
            "ask": 162.45,
            "bid_ask_spread": 0.06,
            "market_cap": 263000000000,
            "sector": "Technology",
            "industry": "Semiconductors",
        },
        "NVDA": {
            "current_price": 910.20,
            "previous_close": 892.50,
            "change_percent": 1.98,
            "day_high": 918.00,
            "day_low": 889.20,
            "volume": 51200000,
            "average_volume": 39000000,
            "bid": 910.05,
            "ask": 910.45,
            "bid_ask_spread": 0.04,
            "market_cap": 2240000000000,
            "sector": "Technology",
            "industry": "Semiconductors",
        },
        "AAPL": {
            "current_price": 191.80,
            "previous_close": 189.95,
            "change_percent": 0.97,
            "day_high": 192.70,
            "day_low": 188.90,
            "volume": 48100000,
            "average_volume": 53000000,
            "bid": 191.75,
            "ask": 191.84,
            "bid_ask_spread": 0.05,
            "market_cap": 2960000000000,
            "sector": "Technology",
            "industry": "Consumer Electronics",
        },
        "MSFT": {
            "current_price": 430.10,
            "previous_close": 426.50,
            "change_percent": 0.84,
            "day_high": 432.00,
            "day_low": 425.80,
            "volume": 22100000,
            "average_volume": 26000000,
            "bid": 430.02,
            "ask": 430.18,
            "bid_ask_spread": 0.04,
            "market_cap": 3190000000000,
            "sector": "Technology",
            "industry": "Software",
        },
        "BTC-USD": {
            "current_price": 68420.00,
            "previous_close": 67100.00,
            "change_percent": 1.97,
            "day_high": 69120.00,
            "day_low": 66840.00,
            "volume": 32000000000,
            "average_volume": 28500000000,
            "bid": 68415.00,
            "ask": 68428.00,
            "bid_ask_spread": 0.02,
            "market_cap": 1340000000000,
            "sector": "Crypto",
            "industry": "Bitcoin",
        },
    }

    def get_snapshot(self, symbol: str) -> Dict[str, Any]:
        values = self.snapshots.get(symbol.upper())
        if not values:
            base_price = 100.0
            values = {
                "current_price": base_price,
                "previous_close": base_price * 0.99,
                "change_percent": 1.0,
                "day_high": base_price * 1.02,
                "day_low": base_price * 0.98,
                "volume": 1000000,
                "average_volume": 1000000,
                "bid": base_price - 0.02,
                "ask": base_price + 0.02,
                "bid_ask_spread": 0.04,
                "market_cap": None,
                "sector": "Unknown",
                "industry": "Unknown",
            }
        values = dict(values)
        values["source_fields_used"] = {"price_source": "mock.current_price", "previous_close_source": "mock.previous_close"}
        response = self._response(
            symbol=symbol,
            data_quality="mock_fallback",
            values=values,
            unavailable_fields=[field for field in MARKET_DATA_FIELDS if values.get(field) is None],
        )
        response["is_mock"] = True
        return response
