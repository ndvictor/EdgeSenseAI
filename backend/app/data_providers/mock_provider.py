from app.data_providers.base import MarketCandle, MarketCandlesResponse, MarketSnapshot


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

    def get_candles(self, symbol: str, period: str = "1mo", interval: str = "1d", asset_class: str = "stock") -> MarketCandlesResponse:
        snapshot = self.get_snapshot(symbol, asset_class)
        closes = [snapshot.current_price * (0.94 + i * 0.0035) for i in range(24)]
        candles = [
            MarketCandle(
                time=f"2026-01-{index + 1:02d}T00:00:00",
                open=round(close * 0.995, 4),
                high=round(close * 1.012, 4),
                low=round(close * 0.988, 4),
                close=round(close, 4),
                volume=max(1, int(snapshot.volume * (0.65 + index * 0.015))),
            )
            for index, close in enumerate(closes)
        ]
        return MarketCandlesResponse(
            symbol=snapshot.symbol,
            asset_class=snapshot.asset_class,
            interval=interval,
            period=period,
            data_mode="synthetic_prototype",
            candles=candles,
        )

    def get_watchlist_snapshots(self) -> list[MarketSnapshot]:
        return list(self.snapshots.values())
