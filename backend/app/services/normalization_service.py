from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from app.data_providers.base import MarketSnapshot


class NormalizedCandle(BaseModel):
    timestamp: datetime
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | None = None
    provider: str | None = None
    data_source: str = "placeholder"


class NormalizedMarketSnapshot(BaseModel):
    ticker: str
    asset_class: str = "stock"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    provider: str | None = None
    data_source: str = "placeholder"
    price: float | None = None
    previous_close: float | None = None
    change_percent: float | None = None
    day_high: float | None = None
    day_low: float | None = None
    volume: float | None = None
    average_volume: float | None = None
    bid: float | None = None
    ask: float | None = None
    bid_ask_spread: float | None = None
    relative_volume: float | None = None
    spread_percent: float | None = None
    vwap: float | None = None
    volatility_proxy: float | None = None
    data_quality: str = "unavailable"
    is_mock: bool = False

    def to_market_snapshot(self) -> MarketSnapshot:
        price = float(self.price or 0)
        previous_close = float(self.previous_close or price or 0)
        change_percent = float(self.change_percent or 0)
        average_volume = float(self.average_volume or self.volume or 1)
        volume = float(self.volume or 0)
        bid = float(self.bid if self.bid is not None else price * 0.999 if price else 0)
        ask = float(self.ask if self.ask is not None else price * 1.001 if price else 0)
        spread_percent = self.spread_percent
        if spread_percent is None and price and bid and ask:
            spread_percent = ((ask - bid) / price) * 100
        return MarketSnapshot(
            symbol=self.ticker,
            asset_class=self.asset_class,
            current_price=price,
            previous_close=previous_close,
            day_change_percent=change_percent,
            volume=int(volume),
            relative_volume=float(self.relative_volume or (volume / average_volume if average_volume else 1)),
            bid=bid,
            ask=ask,
            spread_percent=float(spread_percent or 0),
            vwap=float(self.vwap or price),
            volatility_proxy=float(self.volatility_proxy or 0.3),
            data_mode=self.data_source,
        )


class NormalizedOptionsSnapshot(BaseModel):
    ticker: str
    underlying: str
    expiration: str | None = None
    strike: float | None = None
    option_type: str | None = None
    bid: float | None = None
    ask: float | None = None
    open_interest: float | None = None
    implied_volatility: float | None = None
    provider: str | None = None
    data_source: str = "placeholder"


class NormalizedNewsEvent(BaseModel):
    id: str
    ticker: str | None = None
    headline: str
    source: str | None = None
    published_at: datetime | None = None
    sentiment_score: float | None = None
    data_source: str = "placeholder"


class NormalizedMacroSnapshot(BaseModel):
    name: str
    value: float | str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    provider: str | None = None
    data_source: str = "placeholder"


def normalize_market_snapshot(snapshot: dict[str, Any], asset_class: str = "stock", data_source: str | None = None) -> NormalizedMarketSnapshot:
    price = snapshot.get("price") if snapshot.get("price") is not None else snapshot.get("current_price")
    previous_close = snapshot.get("previous_close")
    volume = snapshot.get("volume")
    average_volume = snapshot.get("average_volume") or volume
    bid = snapshot.get("bid")
    ask = snapshot.get("ask")
    spread = snapshot.get("bid_ask_spread")
    spread_percent = None
    if price and spread is not None:
        spread_percent = (float(spread) / float(price)) * 100
    elif price and bid is not None and ask is not None:
        spread_percent = ((float(ask) - float(bid)) / float(price)) * 100
    return NormalizedMarketSnapshot(
        ticker=str(snapshot.get("symbol") or snapshot.get("ticker") or "UNKNOWN").upper(),
        asset_class=asset_class,
        provider=snapshot.get("provider"),
        data_source=data_source or snapshot.get("data_source") or ("demo" if snapshot.get("is_mock") else "source_backed" if snapshot.get("provider") else "placeholder"),
        price=price,
        previous_close=previous_close,
        change_percent=snapshot.get("change_percent") or snapshot.get("day_change_percent"),
        day_high=snapshot.get("day_high"),
        day_low=snapshot.get("day_low"),
        volume=volume,
        average_volume=average_volume,
        bid=bid,
        ask=ask,
        bid_ask_spread=spread,
        relative_volume=(float(volume) / float(average_volume)) if volume and average_volume else snapshot.get("relative_volume"),
        spread_percent=spread_percent,
        vwap=snapshot.get("vwap") or price,
        volatility_proxy=snapshot.get("volatility_proxy") or 0.3,
        data_quality=snapshot.get("data_quality") or "unavailable",
        is_mock=bool(snapshot.get("is_mock", False)),
    )
