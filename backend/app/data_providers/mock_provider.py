from app.core.production_safety import allow_mock_market_data
from app.data_providers.base import MarketCandle, MarketCandlesResponse, MarketSnapshot


class MockMarketDataProvider:
    """Deterministic mock candles/snapshots for tests and local dev only."""

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
            data_mode="synthetic_prototype",
            is_mock=True,
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
            data_mode="synthetic_prototype",
            is_mock=True,
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
            data_mode="synthetic_prototype",
            is_mock=True,
        ),
    }

    def _guard(self) -> None:
        if not allow_mock_market_data():
            raise PermissionError("mock_market_data_disabled")

    def _unknown_snapshot(self, symbol: str, asset_class: str) -> MarketSnapshot:
        """Unknown symbols must not alias to another ticker."""
        return MarketSnapshot(
            symbol=symbol.upper(),
            asset_class=asset_class,
            current_price=0.0,
            previous_close=0.0,
            day_change_percent=0.0,
            volume=0,
            relative_volume=0.0,
            bid=0.0,
            ask=0.0,
            spread_percent=0.0,
            vwap=0.0,
            volatility_proxy=0.0,
            data_mode="source_unavailable",
            is_mock=True,
        )

    def get_snapshot(self, symbol: str, asset_class: str = "stock") -> MarketSnapshot:
        self._guard()
        sym = symbol.upper()
        if sym not in self.snapshots:
            return self._unknown_snapshot(sym, asset_class)
        return self.snapshots[sym]

    def get_candles(self, symbol: str, period: str = "1mo", interval: str = "1d", asset_class: str = "stock") -> MarketCandlesResponse:
        self._guard()
        snapshot = self.get_snapshot(symbol, asset_class)
        if snapshot.data_mode == "source_unavailable":
            return MarketCandlesResponse(
                symbol=symbol.upper(),
                asset_class=asset_class,
                interval=interval,
                period=period,
                data_mode="source_unavailable",
                candles=[],
            )
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
        self._guard()
        return list(self.snapshots.values())
