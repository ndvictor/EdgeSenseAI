from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ResearchTimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ModelArtifactRecord(Base, ResearchTimestampMixin):
    __tablename__ = "model_artifacts"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    model_key: Mapped[str] = mapped_column(String(160), index=True)
    artifact_version: Mapped[str] = mapped_column(String(120), index=True)
    artifact_type: Mapped[str] = mapped_column(String(80))
    artifact_uri: Mapped[str | None] = mapped_column(Text)
    artifact_hash: Mapped[str | None] = mapped_column(String(160))
    provider: Mapped[str | None] = mapped_column(String(120))
    source: Mapped[str] = mapped_column(String(80), default="manual")
    status: Mapped[str] = mapped_column(String(80), default="missing", index=True)
    trained_on_start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trained_on_end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    feature_version: Mapped[str | None] = mapped_column(String(120))
    label_definition: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(String(120))
    metadata_json: Mapped[dict | list] = mapped_column("metadata", JSON, default=dict)


class ModelEvaluationRunRecord(Base):
    __tablename__ = "model_evaluation_runs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    model_key: Mapped[str] = mapped_column(String(160), index=True)
    artifact_id: Mapped[str | None] = mapped_column(String(80), index=True)
    evaluation_type: Mapped[str] = mapped_column(String(100))
    dataset_source: Mapped[str] = mapped_column(String(120))
    dataset_start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dataset_end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(80), default="pending", index=True)
    passed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    metrics: Mapped[dict | list] = mapped_column(JSON, default=dict)
    minimum_requirements: Mapped[dict | list] = mapped_column(JSON, default=dict)
    failure_reasons: Mapped[dict | list] = mapped_column(JSON, default=list)
    warnings: Mapped[dict | list] = mapped_column(JSON, default=list)
    created_by: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict | list] = mapped_column("metadata", JSON, default=dict)


class ModelCalibrationRunRecord(Base):
    __tablename__ = "model_calibration_runs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    model_key: Mapped[str] = mapped_column(String(160), index=True)
    artifact_id: Mapped[str | None] = mapped_column(String(80), index=True)
    calibration_type: Mapped[str] = mapped_column(String(100))
    dataset_source: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(80), default="pending", index=True)
    passed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    metrics: Mapped[dict | list] = mapped_column(JSON, default=dict)
    calibration_report: Mapped[dict | list] = mapped_column(JSON, default=dict)
    failure_reasons: Mapped[dict | list] = mapped_column(JSON, default=list)
    warnings: Mapped[dict | list] = mapped_column(JSON, default=list)
    created_by: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict | list] = mapped_column("metadata", JSON, default=dict)


class ModelPromotionReviewRecord(Base):
    __tablename__ = "model_promotion_reviews"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    model_key: Mapped[str] = mapped_column(String(160), index=True)
    artifact_id: Mapped[str | None] = mapped_column(String(80), index=True)
    evaluation_run_id: Mapped[str | None] = mapped_column(String(80), index=True)
    calibration_run_id: Mapped[str | None] = mapped_column(String(80), index=True)
    requested_status: Mapped[str] = mapped_column(String(80))
    decision: Mapped[str] = mapped_column(String(80), default="pending", index=True)
    owner_approved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(120))
    review_notes: Mapped[str | None] = mapped_column(Text)
    risk_gate_required: Mapped[bool] = mapped_column(Boolean, default=True)
    human_approval_required: Mapped[bool] = mapped_column(Boolean, default=True)
    final_trade_decision_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    live_scoring_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict | list] = mapped_column("metadata", JSON, default=dict)


class StrategyBacktestRunRecord(Base):
    __tablename__ = "strategy_backtest_runs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    strategy_key: Mapped[str] = mapped_column(String(160), index=True)
    run_type: Mapped[str] = mapped_column(String(100))
    dataset_source: Mapped[str] = mapped_column(String(120))
    dataset_start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dataset_end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    symbols: Mapped[dict | list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(80), default="pending", index=True)
    passed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    metrics: Mapped[dict | list] = mapped_column(JSON, default=dict)
    assumptions: Mapped[dict | list] = mapped_column(JSON, default=dict)
    failure_reasons: Mapped[dict | list] = mapped_column(JSON, default=list)
    warnings: Mapped[dict | list] = mapped_column(JSON, default=list)
    created_by: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict | list] = mapped_column("metadata", JSON, default=dict)


class ModelBacktestRunRecord(Base):
    __tablename__ = "model_backtest_runs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    model_key: Mapped[str] = mapped_column(String(160), index=True)
    artifact_id: Mapped[str | None] = mapped_column(String(80), index=True)
    run_type: Mapped[str] = mapped_column(String(100))
    dataset_source: Mapped[str] = mapped_column(String(120))
    dataset_start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dataset_end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    symbols: Mapped[dict | list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(80), default="pending", index=True)
    passed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    metrics: Mapped[dict | list] = mapped_column(JSON, default=dict)
    assumptions: Mapped[dict | list] = mapped_column(JSON, default=dict)
    failure_reasons: Mapped[dict | list] = mapped_column(JSON, default=list)
    warnings: Mapped[dict | list] = mapped_column(JSON, default=list)
    created_by: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict | list] = mapped_column("metadata", JSON, default=dict)


class ResearchExperimentRunRecord(Base):
    __tablename__ = "research_experiment_runs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    experiment_key: Mapped[str] = mapped_column(String(160), index=True)
    experiment_type: Mapped[str] = mapped_column(String(120), index=True)
    target_type: Mapped[str] = mapped_column(String(80), index=True)
    target_key: Mapped[str] = mapped_column(String(160), index=True)
    priority: Mapped[int] = mapped_column(Integer, default=50, index=True)
    status: Mapped[str] = mapped_column(String(80), default="queued", index=True)
    objective: Mapped[str] = mapped_column(Text)
    input_payload: Mapped[dict | list] = mapped_column(JSON, default=dict)
    output_payload: Mapped[dict | list] = mapped_column(JSON, default=dict)
    blockers: Mapped[dict | list] = mapped_column(JSON, default=list)
    warnings: Mapped[dict | list] = mapped_column(JSON, default=list)
    created_by: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict | list] = mapped_column("metadata", JSON, default=dict)
