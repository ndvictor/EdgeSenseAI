from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, JSON, String, Text
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

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    recommendation_id: Mapped[str | None] = mapped_column(String(80), index=True)
    symbol: Mapped[str] = mapped_column(String(40), index=True)
    asset_class: Mapped[str] = mapped_column(String(40), default="stock")
    horizon: Mapped[str] = mapped_column(String(40), default="swing")
    action: Mapped[str | None] = mapped_column(String(40))
    entry_price: Mapped[float | None] = mapped_column(Float)
    exit_price: Mapped[float | None] = mapped_column(Float)
    stop_loss: Mapped[float | None] = mapped_column(Float)
    target_price: Mapped[float | None] = mapped_column(Float)
    quantity: Mapped[float | None] = mapped_column(Float)
    pnl: Mapped[float | None] = mapped_column(Float)
    pnl_percent: Mapped[float | None] = mapped_column(Float)
    outcome_label: Mapped[str | None] = mapped_column(String(40))
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(40), default="open", index=True)
    notes: Mapped[str | None] = mapped_column(Text)


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


class CandidateUniverseRecord(Base, TimestampMixin):
    __tablename__ = "candidate_universe"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(40), index=True)
    asset_class: Mapped[str] = mapped_column(String(40), default="stock")
    horizon: Mapped[str] = mapped_column(String(40), default="swing")
    source_type: Mapped[str] = mapped_column(String(40))
    source_detail: Mapped[str | None] = mapped_column(Text)
    priority_score: Mapped[int] = mapped_column(Integer, default=50)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    last_ranked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DecisionWorkflowRunRecord(Base, TimestampMixin):
    __tablename__ = "decision_workflow_runs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(80), index=True)
    source: Mapped[str] = mapped_column(String(40))
    horizon: Mapped[str] = mapped_column(String(40))
    symbols_requested: Mapped[dict | list] = mapped_column(JSON, default=list)
    candidates: Mapped[dict | list] = mapped_column(JSON, default=list)
    top_action: Mapped[dict | list | None] = mapped_column(JSON)
    recommendations: Mapped[dict | list] = mapped_column(JSON, default=list)
    feature_runs: Mapped[dict | list] = mapped_column(JSON, default=list)
    model_runs: Mapped[dict | list] = mapped_column(JSON, default=list)
    blockers: Mapped[dict | list] = mapped_column(JSON, default=list)
    warnings: Mapped[dict | list] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)


class RecommendationLifecycleRecord(Base, TimestampMixin):
    __tablename__ = "recommendation_lifecycle"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(40), index=True)
    asset_class: Mapped[str] = mapped_column(String(40), default="stock")
    horizon: Mapped[str] = mapped_column(String(40), default="swing")
    source: Mapped[str | None] = mapped_column(String(40))
    feature_row_id: Mapped[str | None] = mapped_column(String(80))
    score: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    action_label: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40), default="pending_review", index=True)
    reason: Mapped[str | None] = mapped_column(Text)
    risk_factors: Mapped[dict | list] = mapped_column(JSON, default=list)
    workflow_run_id: Mapped[str | None] = mapped_column(String(80), index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ModelTrainingExampleRecord(Base, TimestampMixin):
    __tablename__ = "model_training_examples"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(40), index=True)
    feature_row_id: Mapped[str | None] = mapped_column(String(80))
    recommendation_id: Mapped[str | None] = mapped_column(String(80), index=True)
    paper_trade_outcome_id: Mapped[str | None] = mapped_column(String(80), index=True)
    features: Mapped[dict | list] = mapped_column(JSON, default=dict)
    label: Mapped[dict | list] = mapped_column(JSON, default=dict)
    label_type: Mapped[str] = mapped_column(String(40), default="paper_trade_outcome")


class UpperWorkflowRunRecord(Base):
    __tablename__ = "upper_workflow_runs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(80), index=True)
    horizon: Mapped[str | None] = mapped_column(String(40))
    source: Mapped[str | None] = mapped_column(String(40))
    symbols_requested: Mapped[dict | list] = mapped_column(JSON, default=list)
    market_phase: Mapped[str | None] = mapped_column(String(80))
    active_loop: Mapped[str | None] = mapped_column(String(120))
    data_freshness: Mapped[dict | list | None] = mapped_column(JSON)
    market_regime: Mapped[dict | list | None] = mapped_column(JSON)
    strategy_debate: Mapped[dict | list | None] = mapped_column(JSON)
    strategy_ranking: Mapped[dict | list | None] = mapped_column(JSON)
    model_selection: Mapped[dict | list | None] = mapped_column(JSON)
    universe_selection: Mapped[dict | list | None] = mapped_column(JSON)
    trigger_rules: Mapped[dict | list | None] = mapped_column(JSON)
    event_scanner: Mapped[dict | list | None] = mapped_column(JSON)
    signal_scoring: Mapped[dict | list | None] = mapped_column(JSON)
    meta_model_ensemble: Mapped[dict | list | None] = mapped_column(JSON)
    recommendation_pipeline: Mapped[dict | list | None] = mapped_column(JSON)
    blockers: Mapped[dict | list] = mapped_column(JSON, default=list)
    warnings: Mapped[dict | list] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class TriggerRuleRunRecord(Base):
    __tablename__ = "trigger_rule_runs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(80), index=True)
    strategy_key: Mapped[str | None] = mapped_column(String(120), index=True)
    horizon: Mapped[str | None] = mapped_column(String(40))
    rules: Mapped[dict | list] = mapped_column(JSON, default=list)
    blockers: Mapped[dict | list] = mapped_column(JSON, default=list)
    warnings: Mapped[dict | list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class EventScannerRunRecord(Base):
    __tablename__ = "event_scanner_runs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(80), index=True)
    source: Mapped[str | None] = mapped_column(String(40))
    horizon: Mapped[str | None] = mapped_column(String(40))
    scanned_symbols: Mapped[dict | list] = mapped_column(JSON, default=list)
    matched_events: Mapped[dict | list] = mapped_column(JSON, default=list)
    skipped_symbols: Mapped[dict | list] = mapped_column(JSON, default=list)
    blockers: Mapped[dict | list] = mapped_column(JSON, default=list)
    warnings: Mapped[dict | list] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class SignalScoringRunRecord(Base):
    __tablename__ = "signal_scoring_runs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(80), index=True)
    horizon: Mapped[str | None] = mapped_column(String(40))
    strategy_key: Mapped[str | None] = mapped_column(String(120), index=True)
    scored_signals: Mapped[dict | list] = mapped_column(JSON, default=list)
    blockers: Mapped[dict | list] = mapped_column(JSON, default=list)
    warnings: Mapped[dict | list] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class MetaModelEnsembleRunRecord(Base):
    __tablename__ = "meta_model_ensemble_runs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(80), index=True)
    horizon: Mapped[str | None] = mapped_column(String(40))
    strategy_key: Mapped[str | None] = mapped_column(String(120), index=True)
    ensemble_signals: Mapped[dict | list] = mapped_column(JSON, default=list)
    model_weights_used: Mapped[dict | list] = mapped_column(JSON, default=dict)
    blockers: Mapped[dict | list] = mapped_column(JSON, default=list)
    warnings: Mapped[dict | list] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class RecommendationPipelineRunRecord(Base):
    __tablename__ = "recommendation_pipeline_runs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(80), index=True)
    symbol: Mapped[str | None] = mapped_column(String(40), index=True)
    llm_budget_gate: Mapped[dict | list | None] = mapped_column(JSON)
    agent_validation: Mapped[dict | list | None] = mapped_column(JSON)
    risk_review: Mapped[dict | list | None] = mapped_column(JSON)
    no_trade: Mapped[dict | list | None] = mapped_column(JSON)
    capital_allocation: Mapped[dict | list | None] = mapped_column(JSON)
    recommendation: Mapped[dict | list | None] = mapped_column(JSON)
    blockers: Mapped[dict | list] = mapped_column(JSON, default=list)
    warnings: Mapped[dict | list] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class JournalOutcomeRecord(Base):
    __tablename__ = "journal_outcomes"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(80))
    source_id: Mapped[str | None] = mapped_column(String(100))
    symbol: Mapped[str | None] = mapped_column(String(40), index=True)
    asset_class: Mapped[str | None] = mapped_column(String(40), default="stock")
    horizon: Mapped[str | None] = mapped_column(String(40), default="swing")
    strategy_key: Mapped[str | None] = mapped_column(String(120), index=True)
    regime: Mapped[str | None] = mapped_column(String(80))
    model_stack: Mapped[dict | list] = mapped_column(JSON, default=list)
    expected_outcome: Mapped[str | None] = mapped_column(Text)
    actual_outcome: Mapped[str | None] = mapped_column(Text)
    outcome_label: Mapped[str] = mapped_column(String(60), default="unknown", index=True)
    entry_price: Mapped[float | None] = mapped_column(Float)
    exit_price: Mapped[float | None] = mapped_column(Float)
    target_price: Mapped[float | None] = mapped_column(Float)
    stop_loss: Mapped[float | None] = mapped_column(Float)
    max_favorable_price: Mapped[float | None] = mapped_column(Float)
    max_adverse_price: Mapped[float | None] = mapped_column(Float)
    mfe_percent: Mapped[float | None] = mapped_column(Float)
    mae_percent: Mapped[float | None] = mapped_column(Float)
    realized_r: Mapped[float | None] = mapped_column(Float)
    time_to_result_minutes: Mapped[float | None] = mapped_column(Float)
    followed_plan: Mapped[bool | None] = mapped_column(Boolean)
    confidence_error: Mapped[float | None] = mapped_column(Float)
    expected_vs_actual: Mapped[str | None] = mapped_column(Text)
    lessons: Mapped[dict | list] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[dict | list] = mapped_column(JSON, default=list)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class PerformanceDriftRunRecord(Base):
    __tablename__ = "performance_drift_runs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(80), index=True)
    sample_count: Mapped[int | None] = mapped_column(Integer, default=0)
    lookback_days: Mapped[int | None] = mapped_column(Integer)
    strategy_key: Mapped[str | None] = mapped_column(String(120), index=True)
    model_name: Mapped[str | None] = mapped_column(String(120))
    calibration_buckets: Mapped[dict | list] = mapped_column(JSON, default=list)
    false_positive_rate: Mapped[float | None] = mapped_column(Float)
    win_rate: Mapped[float | None] = mapped_column(Float)
    average_realized_r: Mapped[float | None] = mapped_column(Float)
    confidence_error: Mapped[float | None] = mapped_column(Float)
    affected_models: Mapped[dict | list] = mapped_column(JSON, default=list)
    affected_strategies: Mapped[dict | list] = mapped_column(JSON, default=list)
    recommended_actions: Mapped[dict | list] = mapped_column(JSON, default=list)
    blockers: Mapped[dict | list] = mapped_column(JSON, default=list)
    warnings: Mapped[dict | list] = mapped_column(JSON, default=list)
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ResearchPriorityRunRecord(Base):
    __tablename__ = "research_priority_runs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(80), index=True)
    tasks: Mapped[dict | list] = mapped_column(JSON, default=list)
    blockers: Mapped[dict | list] = mapped_column(JSON, default=list)
    warnings: Mapped[dict | list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ModelStrategyUpdateRunRecord(Base):
    __tablename__ = "model_strategy_update_runs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(80), index=True)
    strategy_weight_updates: Mapped[dict | list] = mapped_column(JSON, default=list)
    model_weight_updates: Mapped[dict | list] = mapped_column(JSON, default=list)
    paused_strategies: Mapped[dict | list] = mapped_column(JSON, default=list)
    retraining_requests: Mapped[dict | list] = mapped_column(JSON, default=list)
    evaluation_jobs: Mapped[dict | list] = mapped_column(JSON, default=list)
    blockers: Mapped[dict | list] = mapped_column(JSON, default=list)
    warnings: Mapped[dict | list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class MemoryUpdateRunRecord(Base):
    __tablename__ = "memory_update_runs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(80), index=True)
    source_type: Mapped[str | None] = mapped_column(String(80), index=True)
    source_id: Mapped[str | None] = mapped_column(String(100))
    memory_id: Mapped[str | None] = mapped_column(String(100))
    title: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict | list] = mapped_column("metadata", JSON, default=dict)
    blockers: Mapped[dict | list] = mapped_column(JSON, default=list)
    warnings: Mapped[dict | list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


# -----------------------------
# Agent Runtime persistence v1
# -----------------------------
class AgentWorkflowRunRecord(Base):
    __tablename__ = "agent_workflow_runs"

    workflow_run_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    workflow_name: Mapped[str | None] = mapped_column(Text)
    asset_class: Mapped[str | None] = mapped_column(String(40))
    horizon: Mapped[str | None] = mapped_column(String(40))
    mode: Mapped[str | None] = mapped_column(String(40))
    source: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str | None] = mapped_column(String(40), index=True)
    current_stage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_agent_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    stage_states: Mapped[dict | list | None] = mapped_column(JSON)
    agent_run_ids: Mapped[dict | list | None] = mapped_column(JSON)
    blockers: Mapped[dict | list | None] = mapped_column(JSON)
    warnings: Mapped[dict | list | None] = mapped_column(JSON)
    metadata_json: Mapped[dict | list | None] = mapped_column("metadata", JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (Index("ix_agent_workflow_runs_created_at", "created_at"),)


class AgentRunRecord(Base):
    __tablename__ = "agent_runs"

    run_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(String(120), index=True)
    agent_key: Mapped[str] = mapped_column(String(120), index=True)
    status: Mapped[str | None] = mapped_column(String(40), index=True)
    decision: Mapped[dict | list | None] = mapped_column(JSON)
    blockers: Mapped[dict | list | None] = mapped_column(JSON)
    warnings: Mapped[dict | list | None] = mapped_column(JSON)
    next_action: Mapped[str | None] = mapped_column(Text)
    next_agent: Mapped[str | None] = mapped_column(String(120), nullable=True)
    artifacts: Mapped[dict | list | None] = mapped_column(JSON)
    trace_id: Mapped[str | None] = mapped_column(String(120))
    trace: Mapped[dict | list | None] = mapped_column(JSON)
    idempotency_key: Mapped[str | None] = mapped_column(String(200))
    inputs_hash: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    __table_args__ = (
        Index("ix_agent_runs_created_at", "created_at"),
        Index("ix_agent_runs_workflow_run_id", "workflow_run_id"),
        Index("ix_agent_runs_agent_key", "agent_key"),
    )


class AgentIdempotencyIndexRecord(Base):
    __tablename__ = "agent_idempotency_index"

    fingerprint: Mapped[str] = mapped_column(String(120), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(120))
    workflow_run_id: Mapped[str] = mapped_column(String(120))
    agent_key: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


# -----------------------------
# Phase 3 evidence + Qlib tables
# -----------------------------
class ProofRegistryRecord(Base):
    __tablename__ = "proof_registry_records"

    proof_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(40), index=True)
    asset_class: Mapped[str] = mapped_column(String(40))
    horizon: Mapped[str] = mapped_column(String(40))
    strategy_key: Mapped[str] = mapped_column(String(120), index=True)
    model_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    proof_type: Mapped[str] = mapped_column(String(80))
    proof_status: Mapped[str] = mapped_column(String(80), index=True)
    sample_size: Mapped[int] = mapped_column(Integer)
    win_rate: Mapped[float] = mapped_column(Float)
    avg_r_multiple: Mapped[float] = mapped_column(Float)
    sharpe_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_drawdown_r: Mapped[float | None] = mapped_column(Float, nullable=True)
    slippage_fail_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    rule_violation_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    backtest_run_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    paper_run_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source: Mapped[str] = mapped_column(String(120))
    evidence: Mapped[dict | list] = mapped_column(JSON, default=dict)
    blockers: Mapped[dict | list] = mapped_column(JSON, default=list)
    warnings: Mapped[dict | list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index("ix_proof_registry_strategy_asset_horizon", "strategy_key", "asset_class", "horizon"),
        Index("ix_proof_registry_model_key", "model_key"),
    )


class ModelEvidenceRecord(Base):
    __tablename__ = "model_evidence_records"

    evidence_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    model_key: Mapped[str] = mapped_column(String(120), index=True)
    model_name: Mapped[str] = mapped_column(String(200))
    model_family: Mapped[str] = mapped_column(String(120))
    asset_class: Mapped[str] = mapped_column(String(40))
    horizon: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(80), index=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    drift_status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    training_status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    backtest_status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    paper_status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    qlib_artifact_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    metrics: Mapped[dict | list] = mapped_column(JSON, default=dict)
    blockers: Mapped[dict | list] = mapped_column(JSON, default=list)
    warnings: Mapped[dict | list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (Index("ix_model_evidence_key_asset_horizon", "model_key", "asset_class", "horizon"),)


class StrategyEvidenceRecord(Base):
    __tablename__ = "strategy_evidence_records"

    evidence_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    strategy_key: Mapped[str] = mapped_column(String(120), index=True)
    strategy_group: Mapped[str] = mapped_column(String(120))
    asset_class: Mapped[str] = mapped_column(String(40))
    horizon: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(80), index=True)
    strategy_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    regime_fit: Mapped[float | None] = mapped_column(Float, nullable=True)
    proof_status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    selected_model_keys: Mapped[dict | list] = mapped_column(JSON, default=list)
    scanner_needs: Mapped[dict | list] = mapped_column(JSON, default=list)
    data_needs: Mapped[dict | list] = mapped_column(JSON, default=list)
    metrics: Mapped[dict | list] = mapped_column(JSON, default=dict)
    blockers: Mapped[dict | list] = mapped_column(JSON, default=list)
    warnings: Mapped[dict | list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (Index("ix_strategy_evidence_key_asset_horizon", "strategy_key", "asset_class", "horizon"),)


class QlibArtifactRecord(Base):
    __tablename__ = "qlib_artifacts"

    artifact_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    artifact_type: Mapped[str] = mapped_column(String(80))
    model_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    strategy_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    symbol: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    asset_class: Mapped[str] = mapped_column(String(40))
    horizon: Mapped[str] = mapped_column(String(40))
    qlib_available: Mapped[bool] = mapped_column(Boolean, default=False)
    qlib_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    artifact_status: Mapped[str] = mapped_column(String(80), index=True)
    artifact_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    metrics: Mapped[dict | list] = mapped_column(JSON, default=dict)
    scores: Mapped[dict | list] = mapped_column(JSON, default=dict)
    metadata_json: Mapped[dict | list] = mapped_column("metadata", JSON, default=dict)
    blockers: Mapped[dict | list] = mapped_column(JSON, default=list)
    warnings: Mapped[dict | list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index("ix_qlib_artifacts_model_key", "model_key"),
        Index("ix_qlib_artifacts_strategy_key", "strategy_key"),
        Index("ix_qlib_artifacts_created_at", "created_at"),
    )


# -----------------------------
# Phase 4 platform tables
# -----------------------------
class WorkflowOrchestratorRunRecord(Base):
    __tablename__ = "workflow_orchestrator_runs"

    orchestrator_run_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(String(120), index=True)
    status: Mapped[str] = mapped_column(String(80), index=True)
    asset_class: Mapped[str] = mapped_column(String(40))
    horizon: Mapped[str] = mapped_column(String(40))
    mode: Mapped[str] = mapped_column(String(40))
    source: Mapped[str] = mapped_column(String(120))
    symbols: Mapped[dict | list] = mapped_column(JSON, default=list)
    current_stage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_agent_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    stage_timeline: Mapped[dict | list] = mapped_column(JSON, default=list)
    agent_run_ids: Mapped[dict | list] = mapped_column(JSON, default=list)
    blockers: Mapped[dict | list] = mapped_column(JSON, default=list)
    warnings: Mapped[dict | list] = mapped_column(JSON, default=list)
    next_action: Mapped[str] = mapped_column(Text, default="")
    approval_required: Mapped[bool] = mapped_column(Boolean, default=True)
    execution_boundary_reached: Mapped[bool] = mapped_column(Boolean, default=False)
    submitted_order: Mapped[bool] = mapped_column(Boolean, default=False)
    broker_called: Mapped[bool] = mapped_column(Boolean, default=False)
    llm_used: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_json: Mapped[dict | list] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index("ix_workflow_orchestrator_runs_workflow_run_id", "workflow_run_id"),
        Index("ix_workflow_orchestrator_runs_created_at", "created_at"),
    )


class WorkflowApprovalItemRecord(Base):
    __tablename__ = "workflow_approval_items"

    approval_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(String(120), index=True)
    orchestrator_run_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    agent_run_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    approval_type: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(80), index=True)
    requested_action: Mapped[dict | list] = mapped_column(JSON, default=dict)
    risk_summary: Mapped[dict | list] = mapped_column(JSON, default=dict)
    required_approver: Mapped[str | None] = mapped_column(String(120), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    rejected_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    approval_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index("ix_workflow_approval_items_workflow_run_id", "workflow_run_id"),
        Index("ix_workflow_approval_items_status", "status"),
    )


class WorkflowAuditEventRecord(Base):
    __tablename__ = "workflow_audit_events"

    audit_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    workflow_run_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    orchestrator_run_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    agent_run_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    event_type: Mapped[str] = mapped_column(String(120), index=True)
    actor: Mapped[str] = mapped_column(String(120), default="system")
    severity: Mapped[str] = mapped_column(String(40), default="info")
    message: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[dict | list] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    __table_args__ = (
        Index("ix_workflow_audit_events_workflow_run_id", "workflow_run_id"),
        Index("ix_workflow_audit_events_event_type", "event_type"),
        Index("ix_workflow_audit_events_created_at", "created_at"),
    )


class WorkflowScheduleRecord(Base):
    __tablename__ = "workflow_schedules"

    schedule_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    schedule_type: Mapped[str] = mapped_column(String(80))
    cron_expression: Mapped[str | None] = mapped_column(String(120), nullable=True)
    interval_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    workflow_request: Mapped[dict | list] = mapped_column(JSON, default=dict)
    max_runs_per_day: Mapped[int] = mapped_column(Integer, default=50)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (Index("ix_workflow_schedules_enabled", "enabled"),)


class WorkflowRetryEventRecord(Base):
    __tablename__ = "workflow_retry_events"

    retry_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(String(120), index=True)
    orchestrator_run_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    agent_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(80), index=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict | list] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    __table_args__ = (Index("ix_workflow_retry_events_workflow_run_id", "workflow_run_id"),)


class WorkflowGovernanceCheckRecord(Base):
    __tablename__ = "workflow_governance_checks"

    governance_check_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    workflow_run_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    check_scope: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(80), index=True)
    gates: Mapped[dict | list] = mapped_column(JSON, default=dict)
    blockers: Mapped[dict | list] = mapped_column(JSON, default=list)
    warnings: Mapped[dict | list] = mapped_column(JSON, default=list)
    limits: Mapped[dict | list] = mapped_column(JSON, default=dict)
    metadata_json: Mapped[dict | list] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    __table_args__ = (Index("ix_workflow_governance_checks_workflow_run_id", "workflow_run_id"),)
