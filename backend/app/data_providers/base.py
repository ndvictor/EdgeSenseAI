from typing import Protocol
from pydantic import BaseModel


class MarketSnapshot(BaseModel):
    symbol: str
    asset_class: str
    current_price: float
    previous_close: float
    day_change_percent: float
    volume: int
    relative_volume: float
    bid: float
    ask: float
    spread_percent: float
    vwap: float
    volatility_proxy: float
    data_mode: str = "synthetic_prototype"


class MarketCandle(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class MarketCandlesResponse(BaseModel):
    symbol: str
    asset_class: str
    interval: str
    period: str
    data_mode: str
    candles: list[MarketCandle]


class MarketDataProvider(Protocol):
    def get_snapshot(self, symbol: str, asset_class: str = "stock") -> MarketSnapshot:
        """Return a normalized market snapshot for a symbol."""
        ...

    def get_watchlist_snapshots(self) -> list[MarketSnapshot]:
        """Return normalized snapshots for the current prototype watchlist."""
        ...

    def get_candles(self, symbol: str, period: str = "1mo", interval: str = "1d", asset_class: str = "stock") -> MarketCandlesResponse:
        """Return normalized OHLCV candles for charting and feature generation."""
        ...
