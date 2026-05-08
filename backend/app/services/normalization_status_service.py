from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


NormalizationHealth = Literal["ready", "warning", "error", "disabled"]


class NormalizationSummary(BaseModel):
    normalization_status: NormalizationHealth
    supported_payloads: int
    records_normalized_today: int
    warning_count: int
    error_count: int
    last_normalized_at: datetime | None
    next_action: str


class NormalizationPayloadType(BaseModel):
    key: str
    label: str
    status: NormalizationHealth
    input_source: str
    output_schema: str
    required_fields: list[str]
    optional_fields: list[str]
    downstream_consumers: list[str]
    records_normalized_today: int
    last_normalized_at: datetime | None
    warnings: list[str]
    errors: list[str]
    next_action: str


class NormalizationPipelinePosition(BaseModel):
    previous_stage: str
    current_stage: str
    next_stage: str
    downstream_stage: str


class NormalizationStatusResponse(BaseModel):
    status: Literal["ok"]
    data_mode: Literal["summary"]
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    summary: NormalizationSummary
    payload_types: list[NormalizationPayloadType]
    pipeline_position: NormalizationPipelinePosition


def build_normalization_status() -> NormalizationStatusResponse:
    payload_types: list[NormalizationPayloadType] = [
        NormalizationPayloadType(
            key="market_snapshot",
            label="Market Snapshot",
            status="ready",
            input_source="market_data_service",
            output_schema="NormalizedMarketSnapshot",
            required_fields=["ticker", "asset_class", "timestamp", "price", "provider", "data_source"],
            optional_fields=["bid", "ask", "volume", "vwap", "relative_volume", "spread_percent"],
            downstream_consumers=["data_quality", "feature_store"],
            records_normalized_today=0,
            last_normalized_at=None,
            warnings=[],
            errors=[],
            next_action="Normalization is wired; ingest snapshots then normalize for downstream checks.",
        ),
        NormalizationPayloadType(
            key="candle",
            label="Candle",
            status="ready",
            input_source="market_data_service",
            output_schema="NormalizedCandle",
            required_fields=["timestamp", "open", "high", "low", "close", "provider", "data_source"],
            optional_fields=["volume"],
            downstream_consumers=["data_quality", "feature_store"],
            records_normalized_today=0,
            last_normalized_at=None,
            warnings=[],
            errors=[],
            next_action="Ingest candle history, then normalize to a consistent OHLCV schema.",
        ),
        NormalizationPayloadType(
            key="options_snapshot",
            label="Options Snapshot",
            status="ready",
            input_source="market_data_service",
            output_schema="NormalizedOptionsSnapshot",
            required_fields=["ticker", "underlying", "provider", "data_source"],
            optional_fields=["expiration", "strike", "option_type", "bid", "ask", "open_interest", "implied_volatility"],
            downstream_consumers=["data_quality", "feature_store"],
            records_normalized_today=0,
            last_normalized_at=None,
            warnings=[],
            errors=[],
            next_action="Ingest options quotes/greeks, then normalize for contract-level QC.",
        ),
        NormalizationPayloadType(
            key="news_event",
            label="News Event",
            status="ready",
            input_source="market_data_service",
            output_schema="NormalizedNewsEvent",
            required_fields=["id", "headline", "data_source"],
            optional_fields=["ticker", "source", "published_at", "sentiment_score"],
            downstream_consumers=["data_quality", "feature_store"],
            records_normalized_today=0,
            last_normalized_at=None,
            warnings=[],
            errors=[],
            next_action="Ingest news events, then normalize timestamps/fields for scoring.",
        ),
        NormalizationPayloadType(
            key="macro_snapshot",
            label="Macro Snapshot",
            status="ready",
            input_source="market_data_service",
            output_schema="NormalizedMacroSnapshot",
            required_fields=["name", "timestamp", "provider", "data_source"],
            optional_fields=["value"],
            downstream_consumers=["data_quality", "feature_store"],
            records_normalized_today=0,
            last_normalized_at=None,
            warnings=[],
            errors=[],
            next_action="Ingest macro series, then normalize for regime context.",
        ),
    ]

    summary = NormalizationSummary(
        normalization_status="ready",
        supported_payloads=len(payload_types),
        records_normalized_today=0,
        warning_count=0,
        error_count=0,
        last_normalized_at=None,
        next_action="Normalization is available. Run data ingestion, then normalize payloads for quality checks.",
    )

    return NormalizationStatusResponse(
        status="ok",
        data_mode="summary",
        summary=summary,
        payload_types=payload_types,
        pipeline_position=NormalizationPipelinePosition(
            previous_stage="data_ingestion",
            current_stage="normalization",
            next_stage="data_quality",
            downstream_stage="feature_store",
        ),
    )
