from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class MarketScanRunRecord(Base, TimestampMixin):
    __tablename__ = "market_scan_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    trigger_type: Mapped[str | None] = mapped_column(String(40))
    strategy_key: Mapped[str | None] = mapped_column(String(120), index=True)
    symbol: Mapped[str | None] = mapped_column(String(40), index=True)
    asset_class: Mapped[str | None] = mapped_column(String(40))
    horizon: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str | None] = mapped_column(String(80), index=True)
    data_source: Mapped[str | None] = mapped_column(String(80))
    matched_signals: Mapped[dict | list | None] = mapped_column(JSON)
    skipped_signals: Mapped[dict | list | None] = mapped_column(JSON)
    required_agents: Mapped[dict | list | None] = mapped_column(JSON)
    required_models: Mapped[dict | list | None] = mapped_column(JSON)
    safety_state: Mapped[dict | list | None] = mapped_column(JSON)
    metadata_json: Mapped[dict | list | None] = mapped_column("metadata", JSON)
    warnings: Mapped[dict | list | None] = mapped_column(JSON)
    errors: Mapped[dict | list | None] = mapped_column(JSON)


class FeatureStoreRowRecord(Base, TimestampMixin):
    __tablename__ = "feature_store_rows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    ticker: Mapped[str] = mapped_column(String(40), index=True)
    symbol: Mapped[str | None] = mapped_column(String(40), index=True)
    asset_class: Mapped[str | None] = mapped_column(String(40))
    horizon: Mapped[str | None] = mapped_column(String(40), index=True)
    status: Mapped[str | None] = mapped_column(String(80))
    data_source: Mapped[str | None] = mapped_column(String(80))
    feature_values: Mapped[dict | list | None] = mapped_column(JSON)
    metadata_json: Mapped[dict | list | None] = mapped_column("metadata", JSON)


class ModelRunOutputRecord(Base, TimestampMixin):
    __tablename__ = "model_run_outputs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str | None] = mapped_column(String(100), index=True)
    run_id: Mapped[str | None] = mapped_column(String(100), index=True)
    symbol: Mapped[str | None] = mapped_column(String(40), index=True)
    strategy_key: Mapped[str | None] = mapped_column(String(120), index=True)
    asset_class: Mapped[str | None] = mapped_column(String(40))
    horizon: Mapped[str | None] = mapped_column(String(40))
    model_name: Mapped[str | None] = mapped_column(String(120), index=True)
    status: Mapped[str | None] = mapped_column(String(80), index=True)
    data_source: Mapped[str | None] = mapped_column(String(80))
    model_outputs: Mapped[dict | list | None] = mapped_column(JSON)
    feature_values: Mapped[dict | list | None] = mapped_column(JSON)
    metadata_json: Mapped[dict | list | None] = mapped_column("metadata", JSON)
    warnings: Mapped[dict | list | None] = mapped_column(JSON)
    errors: Mapped[dict | list | None] = mapped_column(JSON)


class StrategyWorkflowRunRecord(Base, TimestampMixin):
    __tablename__ = "strategy_workflow_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    source_scan_run_id: Mapped[str | None] = mapped_column(String(100), index=True)
    strategy_key: Mapped[str | None] = mapped_column(String(120), index=True)
    symbol: Mapped[str | None] = mapped_column(String(40), index=True)
    asset_class: Mapped[str | None] = mapped_column(String(40))
    horizon: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str | None] = mapped_column(String(80), index=True)
    data_source: Mapped[str | None] = mapped_column(String(80))
    required_agents: Mapped[dict | list | None] = mapped_column(JSON)
    required_models: Mapped[dict | list | None] = mapped_column(JSON)
    model_outputs: Mapped[dict | list | None] = mapped_column(JSON)
    risk_review: Mapped[dict | list | None] = mapped_column(JSON)
    portfolio_decision: Mapped[dict | list | None] = mapped_column(JSON)
    recommendation: Mapped[dict | list | None] = mapped_column(JSON)
    trace: Mapped[dict | list | None] = mapped_column(JSON)
    metadata_json: Mapped[dict | list | None] = mapped_column("metadata", JSON)
    warnings: Mapped[dict | list | None] = mapped_column(JSON)
    errors: Mapped[dict | list | None] = mapped_column(JSON)


class RecommendationRecord(Base, TimestampMixin):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str | None] = mapped_column(String(100), index=True)
    symbol: Mapped[str | None] = mapped_column(String(40), index=True)
    strategy_key: Mapped[str | None] = mapped_column(String(120), index=True)
    asset_class: Mapped[str | None] = mapped_column(String(40))
    horizon: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str | None] = mapped_column(String(80), index=True)
    data_source: Mapped[str | None] = mapped_column(String(80))
    recommendation: Mapped[dict | list | None] = mapped_column(JSON)
    metadata_json: Mapped[dict | list | None] = mapped_column("metadata", JSON)


class LlmUsageRecord(Base, TimestampMixin):
    __tablename__ = "llm_usage_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str | None] = mapped_column(String(100), index=True)
    symbol: Mapped[str | None] = mapped_column(String(40), index=True)
    strategy_key: Mapped[str | None] = mapped_column(String(120), index=True)
    asset_class: Mapped[str | None] = mapped_column(String(40))
    horizon: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str | None] = mapped_column(String(80), index=True)
    data_source: Mapped[str | None] = mapped_column(String(80))
    provider: Mapped[str | None] = mapped_column(String(80))
    model_name: Mapped[str | None] = mapped_column(String(120))
    agent: Mapped[str | None] = mapped_column(String(120))
    workflow: Mapped[str | None] = mapped_column(String(120))
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    estimated_cost: Mapped[float | None] = mapped_column(Float)
    metadata_json: Mapped[dict | list | None] = mapped_column("metadata", JSON)


class PaperTradeOutcomeRecord(Base, TimestampMixin):
    __tablename__ = "paper_trade_outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str | None] = mapped_column(String(100), index=True)
    symbol: Mapped[str | None] = mapped_column(String(40), index=True)
    strategy_key: Mapped[str | None] = mapped_column(String(120), index=True)
    asset_class: Mapped[str | None] = mapped_column(String(40))
    horizon: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str | None] = mapped_column(String(80), index=True)
    data_source: Mapped[str | None] = mapped_column(String(80))
    metadata_json: Mapped[dict | list | None] = mapped_column("metadata", JSON)


class JournalEntryRecord(Base, TimestampMixin):
    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str | None] = mapped_column(String(100), index=True)
    symbol: Mapped[str | None] = mapped_column(String(40), index=True)
    strategy_key: Mapped[str | None] = mapped_column(String(120), index=True)
    asset_class: Mapped[str | None] = mapped_column(String(40))
    horizon: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str | None] = mapped_column(String(80), index=True)
    data_source: Mapped[str | None] = mapped_column(String(80))
    title: Mapped[str | None] = mapped_column(String(240))
    content: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict | list | None] = mapped_column("metadata", JSON)


class VectorMemoryRecord(Base, TimestampMixin):
    __tablename__ = "vector_memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    memory_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    memory_type: Mapped[str] = mapped_column(String(80), index=True)
    source_type: Mapped[str | None] = mapped_column(String(80), index=True)
    source_id: Mapped[str | None] = mapped_column(String(100), index=True)
    symbol: Mapped[str | None] = mapped_column(String(40), index=True)
    asset_class: Mapped[str | None] = mapped_column(String(40))
    strategy_key: Mapped[str | None] = mapped_column(String(120), index=True)
    horizon: Mapped[str | None] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(240))
    content: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[dict | list | None] = mapped_column(JSON)
    metadata_json: Mapped[dict | list | None] = mapped_column("metadata", JSON)
    embedding: Mapped[dict | list | None] = mapped_column(JSON)
    embedding_model: Mapped[str | None] = mapped_column(String(120))
    importance_score: Mapped[float | None] = mapped_column(Float, default=0.5)
