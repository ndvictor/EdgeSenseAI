from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from app.services.data_quality_service import DataQualityReport, check_market_data_quality
from app.services.feature_engineering_service import build_features
from app.services.market_data_service import MarketDataService
from app.services.normalization_service import NormalizedMarketSnapshot, normalize_market_snapshot


class FeatureStoreRow(BaseModel):
    id: str
    ticker: str
    asset_class: str
    horizon: str
    timestamp: datetime
    data_source: str
    data_quality: str
    technical_score: float | None = None
    momentum_score: float | None = None
    volume_score: float | None = None
    rvol_score: float | None = None
    options_score: float | None = None
    sentiment_score: float | None = None
    volatility_score: float | None = None
    macro_score: float | None = None
    regime_score: float | None = None
    liquidity_score: float | None = None
    confidence: float | None = None
    feature_version: str = "foundation_v1"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FeatureStoreRunRequest(BaseModel):
    symbol: str = "AMD"
    asset_class: str = "stock"
    horizon: Literal["intraday", "day_trade", "swing", "one_month"] | str = "swing"
    source: str = "auto"


class FeatureStoreRunResponse(BaseModel):
    row: FeatureStoreRow
    quality_report: DataQualityReport
    normalized_snapshot: NormalizedMarketSnapshot
    storage_mode: str = "in_memory"
    warnings: list[str] = Field(default_factory=list)


_MARKET_DATA = MarketDataService()
_FEATURE_ROWS: list[FeatureStoreRow] = []


def _build_feature_row(
    normalized: NormalizedMarketSnapshot,
    quality_report: DataQualityReport,
    horizon: str,
) -> FeatureStoreRow:
    features = build_features(normalized.to_market_snapshot())
    confidence = max(0.1, min(0.95, features.composite_feature_score / 100))
    if quality_report.quality_status == "warn":
        confidence = min(confidence, 0.72)
    if quality_report.quality_status == "fail":
        confidence = min(confidence, 0.35)
    return FeatureStoreRow(
        id=f"fs-{uuid4().hex[:12]}",
        ticker=normalized.ticker,
        asset_class=normalized.asset_class,
        horizon=horizon,
        timestamp=normalized.timestamp,
        data_source=normalized.data_source,
        data_quality=quality_report.quality_status,
        technical_score=features.composite_feature_score,
        momentum_score=features.momentum_score,
        volume_score=features.rvol_score,
        rvol_score=features.rvol_score,
        volatility_score=features.volatility_score,
        liquidity_score=features.spread_quality_score,
        confidence=round(confidence, 2),
    )


def store_feature_row(row: FeatureStoreRow) -> FeatureStoreRow:
    _FEATURE_ROWS.append(row)
    return row


def get_latest_feature_rows() -> list[FeatureStoreRow]:
    return sorted(_FEATURE_ROWS, key=lambda row: row.created_at, reverse=True)


def get_feature_rows_for_symbol(symbol: str) -> list[FeatureStoreRow]:
    ticker = symbol.upper()
    return [row for row in get_latest_feature_rows() if row.ticker == ticker]


def get_feature_store_status() -> dict[str, Any]:
    return {
        "storage_mode": "in_memory",
        "row_count": len(_FEATURE_ROWS),
        "symbols": sorted({row.ticker for row in _FEATURE_ROWS}),
        "status": "configured",
        "data_source": "source_backed" if any(row.data_source == "source_backed" for row in _FEATURE_ROWS) else "placeholder",
    }


def run_feature_store_pipeline(request: FeatureStoreRunRequest) -> FeatureStoreRunResponse:
    snapshot = _MARKET_DATA.get_market_snapshot(request.symbol, source=request.source)
    quality_report = check_market_data_quality(
        request.symbol,
        asset_class=request.asset_class,
        source=request.source,
        snapshot=snapshot,
    )
    normalized = normalize_market_snapshot(snapshot, asset_class=request.asset_class, data_source=quality_report.data_source)
    row = store_feature_row(_build_feature_row(normalized, quality_report, request.horizon))
    return FeatureStoreRunResponse(
        row=row,
        quality_report=quality_report,
        normalized_snapshot=normalized,
        warnings=quality_report.warnings,
    )
