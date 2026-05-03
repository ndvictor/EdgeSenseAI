from typing import Any

from app.db.init_db import init_db
from app.db.models import (
    FeatureStoreRowRecord,
    JournalEntryRecord,
    LlmUsageRecord,
    MarketScanRunRecord,
    ModelRunOutputRecord,
    PaperTradeOutcomeRecord,
    RecommendationRecord,
    StrategyWorkflowRunRecord,
)
from app.db.session import check_database_health, open_session


def _dump(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, dict):
        return obj
    return dict(obj)


def _try_save(record: Any) -> dict[str, Any]:
    init_db()
    session = open_session()
    if session is None:
        return {"persisted": False, "data_source": "in_memory_fallback", "warning": "Postgres session unavailable."}
    try:
        session.add(record)
        session.commit()
        return {"persisted": True, "data_source": "postgres", "warning": None}
    except Exception as exc:
        session.rollback()
        return {"persisted": False, "data_source": "in_memory_fallback", "warning": str(exc)}
    finally:
        session.close()


def get_persistence_status() -> dict[str, Any]:
    health = check_database_health()
    return {
        "postgres_persistence_status": "connected" if health.get("connected") else "in_memory_fallback",
        "pgvector_status": health.get("pgvector_status", "unknown"),
        "message": health.get("message"),
        "data_source": "postgres" if health.get("connected") else "in_memory_fallback",
    }


def save_market_scan_run(run: Any) -> dict[str, Any]:
    data = _dump(run)
    symbols = data.get("symbols") or []
    return _try_save(MarketScanRunRecord(run_id=data.get("run_id"), trigger_type=data.get("trigger_type"), strategy_key=data.get("strategy_key"), symbol=symbols[0] if symbols else None, status=data.get("status"), data_source=data.get("data_source"), matched_signals=data.get("matched_signals", []), skipped_signals=data.get("skipped_signals", []), required_agents=data.get("required_agents", []), required_models=data.get("required_models", []), safety_state=data.get("safety_state", {}), metadata_json=data, warnings=data.get("warnings", []), errors=data.get("errors", [])))


def list_market_scan_runs(limit: int = 25) -> list[dict[str, Any]]:
    return _list_records(MarketScanRunRecord, limit)


def get_latest_market_scan_run() -> dict[str, Any] | None:
    rows = list_market_scan_runs(1)
    return rows[0] if rows else None


def save_feature_store_row(row: Any) -> dict[str, Any]:
    data = _dump(row)
    return _try_save(FeatureStoreRowRecord(external_id=data.get("id"), ticker=data.get("ticker"), symbol=data.get("ticker"), asset_class=data.get("asset_class"), horizon=data.get("horizon"), status=data.get("data_quality"), data_source=data.get("data_source"), feature_values=data, metadata_json=data))


def list_feature_store_rows(limit: int = 25) -> list[dict[str, Any]]:
    return _list_records(FeatureStoreRowRecord, limit)


def get_latest_feature_store_row(symbol: str | None = None) -> dict[str, Any] | None:
    rows = list_feature_store_rows(100)
    if symbol:
        rows = [row for row in rows if row.get("ticker") == symbol.upper()]
    return rows[0] if rows else None


def save_model_run_output(output: Any, feature_row: Any | None = None, strategy_key: str | None = None) -> dict[str, Any]:
    data = _dump(output)
    row = _dump(feature_row)
    return _try_save(ModelRunOutputRecord(external_id=data.get("model_name") or data.get("model"), symbol=row.get("ticker"), strategy_key=strategy_key, asset_class=row.get("asset_class"), horizon=row.get("horizon"), model_name=data.get("model_name") or data.get("model"), status=data.get("status"), data_source=data.get("data_source"), model_outputs=data, feature_values=row, metadata_json=data, warnings=data.get("warnings", []), errors=data.get("errors", [])))


def list_model_run_outputs(limit: int = 25) -> list[dict[str, Any]]:
    return _list_records(ModelRunOutputRecord, limit)


def save_strategy_workflow_run(run: Any) -> dict[str, Any]:
    data = _dump(run)
    return _try_save(StrategyWorkflowRunRecord(workflow_run_id=data.get("workflow_run_id"), source_scan_run_id=data.get("source_scan_run_id"), strategy_key=data.get("strategy_key"), symbol=data.get("symbol"), asset_class=data.get("asset_class"), horizon=data.get("horizon"), status=data.get("status"), data_source="source_backed", required_agents=data.get("required_agents", []), required_models=data.get("required_models", []), model_outputs=data.get("model_outputs", []), risk_review=data.get("risk_review", {}), portfolio_decision=data.get("portfolio_decision", {}), recommendation=data.get("recommendation", {}), trace=data.get("trace", []), metadata_json=data, warnings=data.get("warnings", []), errors=data.get("errors", [])))


def list_strategy_workflow_runs(limit: int = 25) -> list[dict[str, Any]]:
    return _list_records(StrategyWorkflowRunRecord, limit)


def get_latest_strategy_workflow_run() -> dict[str, Any] | None:
    rows = list_strategy_workflow_runs(1)
    return rows[0] if rows else None


def save_llm_usage_record(record: Any) -> dict[str, Any]:
    data = _dump(record)
    return _try_save(LlmUsageRecord(external_id=data.get("id"), status=data.get("status"), data_source=data.get("data_source"), provider=data.get("provider"), model_name=data.get("model"), agent=data.get("agent"), workflow=data.get("workflow"), prompt_tokens=data.get("prompt_tokens"), completion_tokens=data.get("completion_tokens"), estimated_cost=data.get("estimated_cost"), metadata_json=data))


def list_llm_usage_records(limit: int = 50) -> list[dict[str, Any]]:
    return _list_records(LlmUsageRecord, limit)


def save_recommendation(recommendation: Any) -> dict[str, Any]:
    data = _dump(recommendation)
    return _try_save(RecommendationRecord(external_id=data.get("id") or data.get("workflow_run_id"), symbol=data.get("symbol"), strategy_key=data.get("strategy_key"), asset_class=data.get("asset_class"), horizon=data.get("horizon"), status=data.get("status") or data.get("action"), data_source=data.get("data_source"), recommendation=data, metadata_json=data))


def save_journal_entry(entry: Any) -> dict[str, Any]:
    data = _dump(entry)
    return _try_save(JournalEntryRecord(external_id=data.get("id"), symbol=data.get("symbol"), strategy_key=data.get("strategy_key"), asset_class=data.get("asset_class"), horizon=data.get("horizon"), status=data.get("status"), data_source=data.get("data_source"), title=data.get("title") or data.get("setup"), content=data.get("content") or data.get("lesson"), metadata_json=data))


def save_paper_trade_outcome(outcome: Any) -> dict[str, Any]:
    data = _dump(outcome)
    return _try_save(PaperTradeOutcomeRecord(external_id=data.get("id"), symbol=data.get("symbol"), strategy_key=data.get("strategy_key"), asset_class=data.get("asset_class"), horizon=data.get("horizon"), status=data.get("status"), data_source=data.get("data_source"), metadata_json=data))


def _list_records(model: Any, limit: int) -> list[dict[str, Any]]:
    init_db()
    session = open_session()
    if session is None:
        return []
    try:
        rows = session.query(model).order_by(model.created_at.desc()).limit(max(1, min(limit, 100))).all()
        return [_record_to_dict(row) for row in rows]
    except Exception:
        return []
    finally:
        session.close()


def _record_to_dict(row: Any) -> dict[str, Any]:
    result = {}
    for column in row.__table__.columns:
        attr = row.__mapper__.get_property_by_column(column).key
        result[column.name] = getattr(row, attr)
    return result
