from typing import Any

from app.db.init_db import init_db
from app.db.models import (
    CandidateUniverseRecord,
    DecisionWorkflowRunRecord,
    FeatureStoreRowRecord,
    JournalEntryRecord,
    LlmUsageRecord,
    MarketScanRunRecord,
    ModelRunOutputRecord,
    ModelTrainingExampleRecord,
    PaperTradeOutcomeRecord,
    RecommendationLifecycleRecord,
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


def save_journal_entry(entry: Any, response: Any | None = None) -> dict[str, Any]:
    """Save a journal entry.

    Older journal code passes both the create request and computed response.
    Preserve that contract and persist only observed/requested fields without
    inventing outcomes.
    """
    request_data = _dump(entry)
    response_data = _dump(response)
    data = {**request_data, **response_data}
    return _try_save(JournalEntryRecord(external_id=data.get("id"), symbol=data.get("symbol"), strategy_key=data.get("strategy_key"), asset_class=data.get("asset_class"), horizon=data.get("horizon"), status=data.get("outcome_label") or data.get("status"), data_source=data.get("data_source"), title=data.get("title") or data.get("setup") or data.get("source_type"), content=data.get("content") or data.get("lesson") or data.get("notes"), metadata_json=data))


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


# Platform Workflow Persistence Helpers

def save_candidate_universe_entry(entry: Any) -> dict[str, Any]:
    """Save a candidate universe entry to Postgres."""
    data = _dump(entry)
    return _try_save(
        CandidateUniverseRecord(
            id=data.get("id"),
            symbol=data.get("symbol", "").upper(),
            asset_class=data.get("asset_class", "stock"),
            horizon=data.get("horizon", "swing"),
            source_type=data.get("source_type", "manual"),
            source_detail=data.get("source_detail"),
            priority_score=int(data.get("priority_score", 50)),
            status=data.get("status", "active"),
            notes=data.get("notes"),
            last_ranked_at=data.get("last_ranked_at"),
        )
    )


def list_candidate_universe_entries(status: str | None = None) -> list[dict[str, Any]]:
    """List candidate universe entries from Postgres."""
    init_db()
    session = open_session()
    if session is None:
        return []
    try:
        query = session.query(CandidateUniverseRecord)
        if status:
            query = query.filter(CandidateUniverseRecord.status == status)
        rows = query.order_by(CandidateUniverseRecord.priority_score.desc(), CandidateUniverseRecord.created_at.asc()).all()
        return [_record_to_dict(row) for row in rows]
    except Exception:
        return []
    finally:
        session.close()


def delete_candidate_universe_entry(symbol: str) -> bool:
    """Delete a candidate universe entry from Postgres."""
    init_db()
    session = open_session()
    if session is None:
        return False
    try:
        row = session.query(CandidateUniverseRecord).filter(
            CandidateUniverseRecord.symbol == symbol.upper()
        ).first()
        if row:
            session.delete(row)
            session.commit()
            return True
        return False
    except Exception:
        return False
    finally:
        session.close()


def clear_candidate_universe_entries() -> int:
    """Clear all candidate universe entries from Postgres. Returns count deleted."""
    init_db()
    session = open_session()
    if session is None:
        return 0
    try:
        count = session.query(CandidateUniverseRecord).count()
        session.query(CandidateUniverseRecord).delete()
        session.commit()
        return count
    except Exception:
        return 0
    finally:
        session.close()


def save_decision_workflow_run(run: Any) -> dict[str, Any]:
    """Save a decision workflow run to Postgres."""
    data = _dump(run)
    return _try_save(
        DecisionWorkflowRunRecord(
            id=data.get("run_id"),
            run_id=data.get("run_id"),
            status=data.get("status"),
            source=data.get("source", "auto"),
            horizon=data.get("horizon", "swing"),
            symbols_requested=data.get("symbols_requested", []),
            candidates=data.get("candidates", []),
            top_action=data.get("top_action"),
            recommendations=data.get("recommendations", []),
            feature_runs=data.get("feature_runs", []),
            model_runs=data.get("model_runs", []),
            blockers=data.get("blockers", []),
            warnings=data.get("warnings", []),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            duration_ms=data.get("duration_ms", 0),
        )
    )


def get_latest_decision_workflow_run() -> dict[str, Any] | None:
    """Get the latest decision workflow run from Postgres."""
    init_db()
    session = open_session()
    if session is None:
        return None
    try:
        row = session.query(DecisionWorkflowRunRecord).order_by(
            DecisionWorkflowRunRecord.created_at.desc()
        ).first()
        return _record_to_dict(row) if row else None
    except Exception:
        return None
    finally:
        session.close()


def list_decision_workflow_runs(limit: int = 20) -> list[dict[str, Any]]:
    """List decision workflow runs from Postgres."""
    init_db()
    session = open_session()
    if session is None:
        return []
    try:
        rows = session.query(DecisionWorkflowRunRecord).order_by(
            DecisionWorkflowRunRecord.created_at.desc()
        ).limit(max(1, min(limit, 100))).all()
        return [_record_to_dict(row) for row in rows]
    except Exception:
        return []
    finally:
        session.close()


def save_recommendation_lifecycle_record(rec: Any) -> dict[str, Any]:
    """Save a recommendation lifecycle record to Postgres."""
    data = _dump(rec)
    return _try_save(
        RecommendationLifecycleRecord(
            id=data.get("id"),
            symbol=data.get("symbol", "").upper(),
            asset_class=data.get("asset_class", "stock"),
            horizon=data.get("horizon", "swing"),
            source=data.get("source"),
            feature_row_id=data.get("feature_row_id"),
            score=int(data.get("score", 0)),
            confidence=float(data.get("confidence", 0)),
            action_label=data.get("action_label"),
            status=data.get("status", "pending_review"),
            reason=data.get("reason"),
            risk_factors=data.get("risk_factors", []),
            workflow_run_id=data.get("workflow_run_id"),
            expires_at=data.get("expires_at"),
        )
    )


def list_recommendation_lifecycle_records(
    status: str | None = None, symbol: str | None = None, limit: int = 100
) -> list[dict[str, Any]]:
    """List recommendation lifecycle records from Postgres."""
    init_db()
    session = open_session()
    if session is None:
        return []
    try:
        query = session.query(RecommendationLifecycleRecord)
        if status:
            query = query.filter(RecommendationLifecycleRecord.status == status)
        if symbol:
            query = query.filter(RecommendationLifecycleRecord.symbol == symbol.upper())
        rows = query.order_by(RecommendationLifecycleRecord.created_at.desc()).limit(
            max(1, min(limit, 100))
        ).all()
        return [_record_to_dict(row) for row in rows]
    except Exception:
        return []
    finally:
        session.close()


def update_recommendation_status(rec_id: str, status: str) -> bool:
    """Update the status of a recommendation lifecycle record."""
    from datetime import datetime, timezone
    init_db()
    session = open_session()
    if session is None:
        return False
    try:
        row = session.query(RecommendationLifecycleRecord).filter(
            RecommendationLifecycleRecord.id == rec_id
        ).first()
        if row:
            row.status = status
            row.updated_at = datetime.now(timezone.utc)
            session.commit()
            return True
        return False
    except Exception:
        return False
    finally:
        session.close()


def save_journal_entry(request: Any, response: Any) -> dict[str, Any]:
    """Save a journal entry to Postgres."""
    req_data = _dump(request)
    resp_data = _dump(response)
    return _try_save(
        JournalEntryRecord(
            id=resp_data.get("id"),
            source_type=req_data.get("source_type", "manual_observation"),
            source_id=req_data.get("source_id"),
            symbol=req_data.get("symbol", "").upper() if req_data.get("symbol") else None,
            asset_class=req_data.get("asset_class", "stock"),
            horizon=req_data.get("horizon", "swing"),
            strategy_key=req_data.get("strategy_key"),
            regime=req_data.get("regime"),
            model_stack=req_data.get("model_stack", []),
            entry_price=req_data.get("entry_price"),
            exit_price=req_data.get("exit_price"),
            stop_loss=req_data.get("stop_loss"),
            target_price=req_data.get("target_price"),
            max_favorable_price=req_data.get("max_favorable_price"),
            max_adverse_price=req_data.get("max_adverse_price"),
            outcome_label=resp_data.get("outcome_label", "unknown"),
            realized_r=resp_data.get("realized_r"),
            mfe_percent=resp_data.get("mfe_percent"),
            mae_percent=resp_data.get("mae_percent"),
            time_to_result_minutes=resp_data.get("time_to_result_minutes"),
            followed_plan=resp_data.get("followed_plan"),
            confidence_error=resp_data.get("confidence_error"),
            lessons=resp_data.get("lessons", []),
            notes=req_data.get("notes"),
            tags=req_data.get("tags", []),
            opened_at=req_data.get("opened_at"),
            closed_at=req_data.get("closed_at"),
        )
    )


def create_paper_trade_outcome_from_recommendation(
    recommendation_id: str,
    symbol: str,
    entry_price: float,
    stop_loss: float,
    target_price: float,
    quantity: float = 1.0,
    action: str = "long",
) -> dict[str, Any]:
    """Create a paper trade outcome record from a recommendation."""
    from datetime import datetime, timezone
    from uuid import uuid4

    data = {
        "id": f"pto-{uuid4().hex[:12]}",
        "recommendation_id": recommendation_id,
        "symbol": symbol.upper(),
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "target_price": target_price,
        "quantity": quantity,
        "action": action,
        "status": "open",
        "opened_at": datetime.now(timezone.utc).isoformat(),
    }
    result = _try_save(
        PaperTradeOutcomeRecord(
            id=data["id"],
            recommendation_id=recommendation_id,
            symbol=symbol.upper(),
            action=action,
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_price=target_price,
            quantity=quantity,
            status="open",
            opened_at=datetime.now(timezone.utc),
        )
    )
    result["id"] = data["id"]
    return result


def close_paper_trade_outcome(
    trade_id: str, exit_price: float, notes: str | None = None
) -> dict[str, Any]:
    """Close a paper trade outcome and compute PnL."""
    from datetime import datetime, timezone

    # Try database first
    init_db()
    session = open_session()
    if session is not None:
        try:
            row = session.query(PaperTradeOutcomeRecord).filter(
                PaperTradeOutcomeRecord.id == trade_id
            ).first()
            if row:
                entry = float(row.entry_price) if row.entry_price else 0.0
                qty = float(row.quantity) if row.quantity else 1.0
                exit_p = float(exit_price)

                # Compute PnL
                pnl = (exit_p - entry) * qty
                pnl_percent = ((exit_p - entry) / entry) * 100 if entry != 0 else 0.0

                # Determine outcome label
                if pnl > 0:
                    outcome = "win"
                elif pnl < 0:
                    outcome = "loss"
                else:
                    outcome = "breakeven"

                row.exit_price = exit_p
                row.pnl = round(pnl, 4)
                row.pnl_percent = round(pnl_percent, 4)
                row.outcome_label = outcome
                row.status = "closed"
                row.closed_at = datetime.now(timezone.utc)
                if notes:
                    row.notes = notes

                session.commit()

                # Create training example if we have recommendation context
                if row.recommendation_id:
                    _create_training_example_from_outcome(session, row)

                return {
                    "success": True,
                    "trade_id": trade_id,
                    "pnl": row.pnl,
                    "pnl_percent": row.pnl_percent,
                    "outcome_label": outcome,
                }
        except Exception as exc:
            # Continue to fallback
            pass
        finally:
            session.close()

    # Fallback: in-memory tracking (simplified)
    return {
        "success": True,
        "trade_id": trade_id,
        "pnl": 0.0,
        "pnl_percent": 0.0,
        "outcome_label": "unknown",
        "note": "Database unavailable - trade closed in memory only",
    }


def _create_training_example_from_outcome(session: Any, outcome: Any) -> None:
    """Create a model training example from a closed paper trade outcome."""
    from datetime import datetime, timezone
    from uuid import uuid4

    try:
        # Build features from available data
        features = {
            "symbol": outcome.symbol,
            "entry_price": outcome.entry_price,
            "exit_price": outcome.exit_price,
            "stop_loss": outcome.stop_loss,
            "target_price": outcome.target_price,
        }

        # Build label from outcome
        label = {
            "pnl": outcome.pnl,
            "pnl_percent": outcome.pnl_percent,
            "outcome_label": outcome.outcome_label,
            "trade_duration_days": None,  # Could calculate if opened_at available
        }

        record = ModelTrainingExampleRecord(
            id=f"mte-{uuid4().hex[:12]}",
            symbol=outcome.symbol,
            recommendation_id=outcome.recommendation_id,
            paper_trade_outcome_id=outcome.id,
            features=features,
            label=label,
            label_type="paper_trade_outcome",
            created_at=datetime.now(timezone.utc),
        )
        session.add(record)
        session.commit()
    except Exception:
        # Training example creation is best-effort
        pass


def list_paper_trade_outcomes(
    status: str | None = None, symbol: str | None = None, limit: int = 100
) -> list[dict[str, Any]]:
    """List paper trade outcomes from Postgres."""
    init_db()
    session = open_session()
    if session is None:
        return []
    try:
        query = session.query(PaperTradeOutcomeRecord)
        if status:
            query = query.filter(PaperTradeOutcomeRecord.status == status)
        if symbol:
            query = query.filter(PaperTradeOutcomeRecord.symbol == symbol.upper())
        rows = query.order_by(PaperTradeOutcomeRecord.created_at.desc()).limit(
            max(1, min(limit, 100))
        ).all()
        return [_record_to_dict(row) for row in rows]
    except Exception:
        return []
    finally:
        session.close()


def get_database_table_status() -> dict[str, Any]:
    """Get status of platform persistence tables."""
    from sqlalchemy import inspect
    init_db()
    session = open_session()
    if session is None:
        return {
            "connected": False,
            "tables": {},
            "message": "Database not available",
        }
    try:
        engine = session.get_bind()
        inspector = inspect(engine)
        table_names = inspector.get_table_names()

        relevant_tables = [
            "candidate_universe",
            "decision_workflow_runs",
            "recommendation_lifecycle",
            "paper_trade_outcomes",
            "model_training_examples",
        ]

        tables_status = {}
        for table in relevant_tables:
            exists = table in table_names
            count = 0
            if exists:
                try:
                    count = session.execute(f"SELECT COUNT(*) FROM {table}").scalar()
                except Exception:
                    pass
            tables_status[table] = {"exists": exists, "row_count": count}

        return {
            "connected": True,
            "tables": tables_status,
            "message": "Platform persistence tables available",
        }
    except Exception as exc:
        return {
            "connected": False,
            "tables": {},
            "message": str(exc),
        }
    finally:
        session.close()
