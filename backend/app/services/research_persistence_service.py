from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.db.init_db import init_db
from app.db.research_models import (
    ModelArtifactRecord,
    ModelBacktestRunRecord,
    ModelCalibrationRunRecord,
    ModelEvaluationRunRecord,
    ModelPromotionReviewRecord,
    ResearchExperimentRunRecord,
    StrategyBacktestRunRecord,
)
from app.db.session import open_session


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def make_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def dump(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    return dict(value)


def record_to_dict(row: Any) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for column in row.__table__.columns:
        attr = row.__mapper__.get_property_by_column(column).key
        result[column.name] = getattr(row, attr)
    return result


def try_save(record: Any) -> dict[str, Any]:
    init_db()
    session = open_session()
    if session is None:
        return {"persisted": False, "data_source": "in_memory_fallback", "warning": "Postgres session unavailable.", "record": record_to_dict(record)}
    try:
        session.add(record)
        session.commit()
        session.refresh(record)
        return {"persisted": True, "data_source": "postgres", "warning": None, "record": record_to_dict(record)}
    except Exception as exc:
        session.rollback()
        return {"persisted": False, "data_source": "in_memory_fallback", "warning": str(exc), "record": record_to_dict(record)}
    finally:
        session.close()


def list_records(model: Any, limit: int = 50, **filters: Any) -> list[dict[str, Any]]:
    init_db()
    session = open_session()
    if session is None:
        return []
    try:
        query = session.query(model)
        for key, value in filters.items():
            if value is not None and hasattr(model, key):
                query = query.filter(getattr(model, key) == value)
        rows = query.order_by(model.created_at.desc()).limit(max(1, min(limit, 500))).all()
        return [record_to_dict(row) for row in rows]
    except Exception:
        return []
    finally:
        session.close()


def get_record(model: Any, record_id: str) -> dict[str, Any] | None:
    init_db()
    session = open_session()
    if session is None:
        return None
    try:
        row = session.query(model).filter(model.id == record_id).first()
        return record_to_dict(row) if row else None
    except Exception:
        return None
    finally:
        session.close()


def latest_record(model: Any, **filters: Any) -> dict[str, Any] | None:
    rows = list_records(model, limit=1, **filters)
    return rows[0] if rows else None


def create_model_artifact(payload: dict[str, Any]) -> dict[str, Any]:
    artifact_uri = payload.get("artifact_uri")
    status = payload.get("status") or ("registered" if artifact_uri or payload.get("artifact_hash") else "missing")
    record = ModelArtifactRecord(
        id=payload.get("id") or make_id("artifact"),
        model_key=payload["model_key"],
        artifact_version=payload.get("artifact_version") or "v0",
        artifact_type=payload.get("artifact_type") or "wrapper",
        artifact_uri=artifact_uri,
        artifact_hash=payload.get("artifact_hash"),
        provider=payload.get("provider"),
        source=payload.get("source") or "manual",
        status=status,
        trained_on_start_date=payload.get("trained_on_start_date"),
        trained_on_end_date=payload.get("trained_on_end_date"),
        feature_version=payload.get("feature_version"),
        label_definition=payload.get("label_definition"),
        created_by=payload.get("created_by"),
        metadata_json=payload.get("metadata") or {},
    )
    return try_save(record)


def list_model_artifacts(model_key: str | None = None) -> list[dict[str, Any]]:
    return list_records(ModelArtifactRecord, model_key=model_key)


def get_model_artifact(artifact_id: str) -> dict[str, Any] | None:
    return get_record(ModelArtifactRecord, artifact_id)


def get_latest_valid_model_artifact(model_key: str) -> dict[str, Any] | None:
    rows = list_records(ModelArtifactRecord, limit=25, model_key=model_key)
    valid = [row for row in rows if row.get("status") == "registered"]
    return valid[0] if valid else None


def create_model_evaluation_run(payload: dict[str, Any]) -> dict[str, Any]:
    record = ModelEvaluationRunRecord(
        id=payload.get("id") or make_id("eval"),
        model_key=payload["model_key"],
        artifact_id=payload.get("artifact_id"),
        evaluation_type=payload.get("evaluation_type") or "research_backtest",
        dataset_source=payload.get("dataset_source") or "manual_metrics",
        dataset_start_date=payload.get("dataset_start_date"),
        dataset_end_date=payload.get("dataset_end_date"),
        status=payload.get("status") or "pending",
        passed=bool(payload.get("passed", False)),
        metrics=payload.get("metrics") or {},
        minimum_requirements=payload.get("minimum_requirements") or {},
        failure_reasons=payload.get("failure_reasons") or [],
        warnings=payload.get("warnings") or [],
        created_by=payload.get("created_by"),
        completed_at=payload.get("completed_at") or now_utc(),
        metadata_json=payload.get("metadata") or {},
    )
    return try_save(record)


def list_model_evaluation_runs(model_key: str | None = None) -> list[dict[str, Any]]:
    return list_records(ModelEvaluationRunRecord, model_key=model_key)


def get_latest_passed_model_evaluation(model_key: str, artifact_id: str | None = None) -> dict[str, Any] | None:
    rows = list_model_evaluation_runs(model_key)
    rows = [row for row in rows if row.get("passed") is True and row.get("status") == "passed"]
    if artifact_id:
        rows = [row for row in rows if row.get("artifact_id") == artifact_id]
    return rows[0] if rows else None


def create_model_calibration_run(payload: dict[str, Any]) -> dict[str, Any]:
    record = ModelCalibrationRunRecord(
        id=payload.get("id") or make_id("calib"),
        model_key=payload["model_key"],
        artifact_id=payload.get("artifact_id"),
        calibration_type=payload.get("calibration_type") or "confidence_calibration",
        dataset_source=payload.get("dataset_source") or "manual_metrics",
        status=payload.get("status") or "pending",
        passed=bool(payload.get("passed", False)),
        metrics=payload.get("metrics") or {},
        calibration_report=payload.get("calibration_report") or {},
        failure_reasons=payload.get("failure_reasons") or [],
        warnings=payload.get("warnings") or [],
        created_by=payload.get("created_by"),
        completed_at=payload.get("completed_at") or now_utc(),
        metadata_json=payload.get("metadata") or {},
    )
    return try_save(record)


def list_model_calibration_runs(model_key: str | None = None) -> list[dict[str, Any]]:
    return list_records(ModelCalibrationRunRecord, model_key=model_key)


def get_latest_passed_model_calibration(model_key: str, artifact_id: str | None = None) -> dict[str, Any] | None:
    rows = list_model_calibration_runs(model_key)
    rows = [row for row in rows if row.get("passed") is True and row.get("status") == "passed"]
    if artifact_id:
        rows = [row for row in rows if row.get("artifact_id") == artifact_id]
    return rows[0] if rows else None


def create_model_promotion_review(payload: dict[str, Any]) -> dict[str, Any]:
    record = ModelPromotionReviewRecord(
        id=payload.get("id") or make_id("promo"),
        model_key=payload["model_key"],
        artifact_id=payload.get("artifact_id"),
        evaluation_run_id=payload.get("evaluation_run_id"),
        calibration_run_id=payload.get("calibration_run_id"),
        requested_status=payload.get("requested_status") or "active_working_model",
        decision=payload.get("decision") or "pending",
        owner_approved=bool(payload.get("owner_approved", False)),
        reviewed_by=payload.get("reviewed_by"),
        review_notes=payload.get("review_notes"),
        risk_gate_required=True,
        human_approval_required=True,
        final_trade_decision_allowed=False,
        live_scoring_allowed=bool(payload.get("live_scoring_allowed", False)),
        reviewed_at=payload.get("reviewed_at"),
        metadata_json=payload.get("metadata") or {},
    )
    return try_save(record)


def list_model_promotion_reviews(model_key: str | None = None) -> list[dict[str, Any]]:
    return list_records(ModelPromotionReviewRecord, model_key=model_key)


def get_latest_approved_model_promotion(model_key: str, artifact_id: str | None = None) -> dict[str, Any] | None:
    rows = list_model_promotion_reviews(model_key)
    rows = [row for row in rows if row.get("decision") == "approved" and row.get("owner_approved") is True]
    if artifact_id:
        rows = [row for row in rows if row.get("artifact_id") == artifact_id]
    return rows[0] if rows else None


def create_strategy_backtest_run(payload: dict[str, Any]) -> dict[str, Any]:
    symbols = payload.get("symbols") or []
    blockers = list(payload.get("failure_reasons") or [])
    status = payload.get("status") or "pending"
    passed = bool(payload.get("passed", False))
    if not symbols:
        status = "blocked"
        passed = False
        blockers.append("No explicit symbols or candidate universe provided.")
    record = StrategyBacktestRunRecord(
        id=payload.get("id") or make_id("stratbt"),
        strategy_key=payload["strategy_key"],
        run_type=payload.get("run_type") or "historical_backtest",
        dataset_source=payload.get("dataset_source") or "manual_request",
        dataset_start_date=payload.get("dataset_start_date"),
        dataset_end_date=payload.get("dataset_end_date"),
        symbols=symbols,
        status=status,
        passed=passed,
        metrics=payload.get("metrics") or {},
        assumptions=payload.get("assumptions") or {},
        failure_reasons=blockers,
        warnings=payload.get("warnings") or [],
        created_by=payload.get("created_by"),
        completed_at=payload.get("completed_at"),
        metadata_json=payload.get("metadata") or {},
    )
    return try_save(record)


def list_strategy_backtest_runs(strategy_key: str | None = None) -> list[dict[str, Any]]:
    return list_records(StrategyBacktestRunRecord, strategy_key=strategy_key)


def create_model_backtest_run(payload: dict[str, Any]) -> dict[str, Any]:
    symbols = payload.get("symbols") or []
    blockers = list(payload.get("failure_reasons") or [])
    status = payload.get("status") or "pending"
    passed = bool(payload.get("passed", False))
    if not symbols:
        status = "blocked"
        passed = False
        blockers.append("No explicit symbols or candidate universe provided.")
    record = ModelBacktestRunRecord(
        id=payload.get("id") or make_id("modelbt"),
        model_key=payload["model_key"],
        artifact_id=payload.get("artifact_id"),
        run_type=payload.get("run_type") or "historical_backtest",
        dataset_source=payload.get("dataset_source") or "manual_request",
        dataset_start_date=payload.get("dataset_start_date"),
        dataset_end_date=payload.get("dataset_end_date"),
        symbols=symbols,
        status=status,
        passed=passed,
        metrics=payload.get("metrics") or {},
        assumptions=payload.get("assumptions") or {},
        failure_reasons=blockers,
        warnings=payload.get("warnings") or [],
        created_by=payload.get("created_by"),
        completed_at=payload.get("completed_at"),
        metadata_json=payload.get("metadata") or {},
    )
    return try_save(record)


def list_model_backtest_runs(model_key: str | None = None) -> list[dict[str, Any]]:
    return list_records(ModelBacktestRunRecord, model_key=model_key)


def get_latest_passed_model_backtest(model_key: str, artifact_id: str | None = None) -> dict[str, Any] | None:
    rows = list_model_backtest_runs(model_key)
    rows = [row for row in rows if row.get("passed") is True and row.get("status") == "passed"]
    if artifact_id:
        rows = [row for row in rows if row.get("artifact_id") == artifact_id]
    return rows[0] if rows else None


def create_research_experiment_run(payload: dict[str, Any]) -> dict[str, Any]:
    record = ResearchExperimentRunRecord(
        id=payload.get("id") or make_id("research"),
        experiment_key=payload.get("experiment_key") or make_id("exp"),
        experiment_type=payload.get("experiment_type") or "model_backtest",
        target_type=payload.get("target_type") or "model",
        target_key=payload["target_key"],
        priority=int(payload.get("priority", 50)),
        status=payload.get("status") or "queued",
        objective=payload.get("objective") or "Research candidate evidence before promotion.",
        input_payload=payload.get("input_payload") or {},
        output_payload=payload.get("output_payload") or {},
        blockers=payload.get("blockers") or [],
        warnings=payload.get("warnings") or [],
        created_by=payload.get("created_by"),
        completed_at=payload.get("completed_at"),
        metadata_json=payload.get("metadata") or {},
    )
    return try_save(record)


def list_research_experiment_runs(target_key: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
    filters: dict[str, Any] = {}
    if target_key:
        filters["target_key"] = target_key
    if status:
        filters["status"] = status
    return list_records(ResearchExperimentRunRecord, **filters)
