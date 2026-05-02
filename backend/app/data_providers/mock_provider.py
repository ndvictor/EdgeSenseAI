from app.data_providers.base import MarketSnapshot


class MockMarketDataProvider:
    """Deterministic provider used until live market data APIs are connected."""

    snapshots = {
        "AMD": MarketSnapshot(
            symbol="AMD",
            asset_class="stock",
            current_price=162.40,
            previous_close=158.90,
            day_change_percent=2.2,
            volume=68420000,
            relative_volume=1.8,
            bid=162.35,
            ask=162.45,
            spread_percent=0.06,
            vwap=160.80,
            volatility_proxy=0.34,
        ),
        "NVDA": MarketSnapshot(
            symbol="NVDA",
            asset_class="stock",
            current_price=910.20,
            previous_close=892.50,
            day_change_percent=1.98,
            volume=51200000,
            relative_volume=2.4,
            bid=910.05,
            ask=910.45,
            spread_percent=0.04,
            vwap=901.10,
            volatility_proxy=0.41,
        ),
        "BTC-USD": MarketSnapshot(
            symbol="BTC-USD",
            asset_class="crypto",
            current_price=68420.00,
            previous_close=67100.00,
            day_change_percent=1.97,
            volume=32000000000,
            relative_volume=1.5,
            bid=68415.00,
            ask=68428.00,
            spread_percent=0.02,
            vwap=67880.00,
            volatility_proxy=0.55,
        ),
    }

    def get_snapshot(self, symbol: str, asset_class: str = "stock") -> MarketSnapshot:
        return self.snapshots.get(symbol, self.snapshots["AMD"])

    def get_watchlist_snapshots(self) -> list[MarketSnapshot]:
        return list(self.snapshots.values())
