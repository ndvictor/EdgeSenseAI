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

"""Normalization status/readiness layer.

Provides a deterministic status payload for the normalization stage.
Does not start jobs or call external providers.
"""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

NormalizationHealth = Literal["ready", "warning", "error", "disabled"]


class NormalizationSummary(BaseModel):
    normalization_status: NormalizationHealth = "ready"
    supported_payloads: int
    records_normalized_today: int = 0
    warning_count: int = 0
    error_count: int = 0
    last_normalized_at: str | None = None
    next_action: str


class NormalizationPayloadType(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    key: str
    label: str
    status: NormalizationHealth = "ready"
    input_source: str = "market_data_service"
    output_schema: str
    required_fields: list[str]
    optional_fields: list[str]
    downstream_consumers: list[str] = Field(default_factory=lambda: ["data_quality", "feature_store"])
    records_normalized_today: int = 0
    last_normalized_at: str | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    next_action: str


class NormalizationPipelinePosition(BaseModel):
    previous_stage: str = "data_ingestion"
    current_stage: str = "normalization"
    next_stage: str = "data_quality"
    downstream_stage: str = "feature_store"


class NormalizationStatusResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    status: Literal["ok"] = "ok"
    data_mode: Literal["summary"] = "summary"
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    summary: NormalizationSummary
    payload_types: list[NormalizationPayloadType]
    pipeline_position: NormalizationPipelinePosition = Field(default_factory=NormalizationPipelinePosition)


def build_normalization_status() -> NormalizationStatusResponse:
    payload_types: list[NormalizationPayloadType] = [
        NormalizationPayloadType(
            key="market_snapshot",
            label="Market Snapshot",
            output_schema="NormalizedMarketSnapshot",
            required_fields=["ticker", "asset_class", "timestamp", "price", "provider", "data_source"],
            optional_fields=["bid", "ask", "volume", "vwap", "relative_volume", "spread_percent"],
            next_action="Ingest market snapshots, then normalize before quality checks and feature storage.",
        ),
        NormalizationPayloadType(
            key="candle",
            label="Candle",
            output_schema="NormalizedCandle",
            required_fields=["timestamp", "open", "high", "low", "close", "provider", "data_source"],
            optional_fields=["volume"],
            next_action="Ingest OHLCV bars, then normalize candles for indicators/features.",
        ),
        NormalizationPayloadType(
            key="options_snapshot",
            label="Options Snapshot",
            output_schema="NormalizedOptionsSnapshot",
            required_fields=["ticker", "underlying", "provider", "data_source"],
            optional_fields=["expiration", "strike", "option_type", "bid", "ask", "open_interest", "implied_volatility"],
            next_action="Wire an options provider, then normalize chains/Greeks/IV surfaces.",
        ),
        NormalizationPayloadType(
            key="news_event",
            label="News Event",
            output_schema="NormalizedNewsEvent",
            required_fields=["id", "headline", "data_source"],
            optional_fields=["ticker", "source", "published_at", "sentiment_score"],
            next_action="Configure a news provider, then normalize events for catalysts and sentiment.",
        ),
        NormalizationPayloadType(
            key="macro_snapshot",
            label="Macro Snapshot",
            output_schema="NormalizedMacroSnapshot",
            required_fields=["name", "timestamp", "provider", "data_source"],
            optional_fields=["value"],
            next_action="Ingest macro series, then normalize for regime context.",
        ),
    ]

    return NormalizationStatusResponse(
        summary=NormalizationSummary(
            supported_payloads=len(payload_types),
            records_normalized_today=0,
            last_normalized_at=None,
            next_action="Normalization is ready. Wire ingestion + persistence counters to reflect real throughput.",
        ),
        payload_types=payload_types,
    )

# from __future__ import annotations

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

