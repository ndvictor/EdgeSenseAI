"""Performance Drift + Calibration Model Service.

Analyzes whether model confidence and strategy scores are reliable based on journal outcomes.

NO fake performance metrics.
NO LLM calls.
Returns insufficient_data when sample count is too low.
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.services.persistence_service import (
    get_latest_performance_drift_run,
    list_performance_drift_runs,
    save_performance_drift_run,
)
from app.services.journal_outcome_service import (
    JournalEntryCreateRequest,
    JournalEntryResponse,
    _JOURNAL_CREATE_REQUESTS,
    _JOURNAL_ENTRIES,
)


class CalibrationBucket(BaseModel):
    """A calibration bucket showing confidence vs observed win rate."""

    model_config = ConfigDict(protected_namespaces=())

    bucket: str  # e.g., "0.0-0.2", "0.2-0.4", etc.
    count: int
    avg_confidence: float
    observed_win_rate: float
    avg_realized_r: float | None
    calibration_error: float  # |avg_confidence - observed_win_rate|


class PerformanceDriftRequest(BaseModel):
    """Request to run performance drift analysis."""

    model_config = ConfigDict(protected_namespaces=())

    lookback_days: int = Field(default=30, ge=1)
    strategy_key: str | None = None
    model_name: str | None = None
    min_samples: int = Field(default=5, ge=1)
    source: Literal["journal", "paper_trades", "both"] = "both"


class PerformanceDriftResponse(BaseModel):
    """Response from performance drift analysis."""

    model_config = ConfigDict(protected_namespaces=())

    run_id: str
    status: Literal["pass", "warn", "fail", "insufficient_data"]
    sample_count: int
    calibration_buckets: list[CalibrationBucket]
    false_positive_rate: float | None = None
    win_rate: float | None = None
    average_realized_r: float | None = None
    confidence_error: float | None = None
    affected_models: list[str] = Field(default_factory=list)
    affected_strategies: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checked_at: datetime


# In-memory storage
_LATEST_DRIFT_CHECK: PerformanceDriftResponse | None = None
_DRIFT_HISTORY: list[PerformanceDriftResponse] = []


def _drift_from_record(row: dict) -> PerformanceDriftResponse | None:
    try:
        return PerformanceDriftResponse.model_validate({
            "run_id": row.get("run_id"),
            "status": row.get("status"),
            "sample_count": row.get("sample_count") or 0,
            "calibration_buckets": row.get("calibration_buckets") or [],
            "false_positive_rate": row.get("false_positive_rate"),
            "win_rate": row.get("win_rate"),
            "average_realized_r": row.get("average_realized_r"),
            "confidence_error": row.get("confidence_error"),
            "affected_models": row.get("affected_models") or [],
            "affected_strategies": row.get("affected_strategies") or [],
            "recommended_actions": row.get("recommended_actions") or [],
            "blockers": row.get("blockers") or [],
            "warnings": row.get("warnings") or [],
            "checked_at": row.get("checked_at") or row.get("created_at"),
        })
    except Exception:
        return None


def _get_relevant_entries(
    lookback_days: int,
    source: str,
    strategy_key: str | None,
    model_name: str | None,
) -> list[tuple[JournalEntryResponse, JournalEntryCreateRequest]]:
    """Get journal entries matching the filter criteria."""
    now = datetime.now(timezone.utc)
    
    results = []
    for entry_id, entry in _JOURNAL_ENTRIES.items():
        # Check source filter
        if source == "paper_trades" and entry.source_type != "paper_trade":
            continue
        if source == "journal" and entry.source_type == "paper_trade":
            continue
        
        # Check lookback
        days_old = (now - entry.created_at).days
        if days_old > lookback_days:
            continue
        
        # Get original request for strategy/model info
        request = _JOURNAL_CREATE_REQUESTS.get(entry_id)
        if request is None:
            continue
        
        # Check strategy filter
        if strategy_key and request.strategy_key != strategy_key:
            continue
        
        # Check model filter
        if model_name and model_name not in request.model_stack:
            continue
        
        results.append((entry, request))
    
    return results


def _compute_calibration_buckets(
    entries: list[tuple[JournalEntryResponse, JournalEntryCreateRequest]],
) -> list[CalibrationBucket]:
    """Compute calibration buckets from entries."""
    if not entries:
        return []
    
    # Define confidence buckets
    buckets = [
        (0.0, 0.2, "0.0-0.2"),
        (0.2, 0.4, "0.2-0.4"),
        (0.4, 0.6, "0.4-0.6"),
        (0.6, 0.8, "0.6-0.8"),
        (0.8, 1.0, "0.8-1.0"),
    ]
    
    bucket_data: dict[str, list[tuple[JournalEntryResponse, JournalEntryCreateRequest]]] = {
        b[2]: [] for b in buckets
    }
    
    # Assign entries to buckets based on confidence
    for entry, request in entries:
        confidence = request.model_stack[0] if request.model_stack else 0.5  # Default mid confidence
        # Try to extract actual confidence from metadata if available
        if request.expected_outcome:
            # Simple heuristic: if expected outcome is strong, assume higher confidence
            if "high" in request.expected_outcome.lower() or "strong" in request.expected_outcome.lower():
                confidence = 0.8
            elif "low" in request.expected_outcome.lower() or "weak" in request.expected_outcome.lower():
                confidence = 0.3
        
        for low, high, name in buckets:
            if low <= confidence < high or (high == 1.0 and confidence == 1.0):
                bucket_data[name].append((entry, request))
                break
    
    calibration_buckets = []
    for low, high, name in buckets:
        bucket_entries = bucket_data[name]
        if not bucket_entries:
            continue
        
        count = len(bucket_entries)
        avg_confidence = (low + high) / 2  # Midpoint of bucket
        
        # Observed win rate
        wins = sum(1 for e, _ in bucket_entries if e.outcome_label == "win")
        observed_win_rate = wins / count
        
        # Average realized R
        realized_rs = [e.realized_r for e, _ in bucket_entries if e.realized_r is not None]
        avg_realized_r = sum(realized_rs) / len(realized_rs) if realized_rs else None
        
        # Calibration error
        calibration_error = abs(avg_confidence - observed_win_rate)
        
        calibration_buckets.append(CalibrationBucket(
            bucket=name,
            count=count,
            avg_confidence=avg_confidence,
            observed_win_rate=observed_win_rate,
            avg_realized_r=avg_realized_r,
            calibration_error=calibration_error,
        ))
    
    return calibration_buckets


def _compute_false_positive_rate(
    entries: list[tuple[JournalEntryResponse, JournalEntryCreateRequest]],
) -> float | None:
    """Compute false positive rate (expected wins that were losses)."""
    # Find entries where we expected a win but got a loss
    false_positives = 0
    total_positive_predictions = 0
    
    for entry, request in entries:
        if request.expected_outcome and "win" in request.expected_outcome.lower():
            total_positive_predictions += 1
            if entry.outcome_label == "loss":
                false_positives += 1
    
    if total_positive_predictions == 0:
        return None
    
    return false_positives / total_positive_predictions


def _compute_confidence_error(
    entries: list[tuple[JournalEntryResponse, JournalEntryCreateRequest]],
) -> float | None:
    """Compute average confidence error."""
    errors = [e.confidence_error for e, _ in entries if e.confidence_error is not None]
    if not errors:
        return None
    return sum(errors) / len(errors)


def _determine_recommended_actions(
    status: str,
    sample_count: int,
    calibration_buckets: list[CalibrationBucket],
    false_positive_rate: float | None,
    win_rate: float | None,
    affected_models: list[str],
    affected_strategies: list[str],
) -> list[str]:
    """Determine recommended actions based on drift analysis."""
    actions = []
    
    if status == "insufficient_data":
        actions.append("collect_more_data")
        return actions
    
    # Check calibration
    high_error_buckets = [b for b in calibration_buckets if b.calibration_error > 0.2 and b.count >= 3]
    if high_error_buckets:
        actions.append("retrain_model")
        actions.append("add_risk_filter")
    
    # Check false positive rate
    if false_positive_rate is not None and false_positive_rate > 0.4:
        actions.append("reduce_weight")
        actions.append("add_risk_filter")
    
    # Check win rate
    if win_rate is not None:
        if win_rate < 0.3:
            actions.append("pause_strategy")
            actions.append("collect_more_data")
        elif win_rate < 0.5:
            actions.append("reduce_weight")
        elif win_rate > 0.6:
            actions.append("keep")
    
    # If no specific actions, default to keep
    if not actions:
        actions.append("keep")
    
    return actions


def run_performance_drift_check(request: PerformanceDriftRequest) -> PerformanceDriftResponse:
    """Run performance drift analysis.
    
    Rules:
    - If insufficient samples, return insufficient_data status
    - Do not invent performance metrics
    - Use actual journal/paper trade outcomes
    - No LLM calls
    """
    run_id = f"drift-{uuid4().hex[:12]}"
    checked_at = datetime.now(timezone.utc)
    
    # Get relevant entries
    entries = _get_relevant_entries(
        request.lookback_days,
        request.source,
        request.strategy_key,
        request.model_name,
    )
    
    sample_count = len(entries)
    
    # Check minimum samples
    if sample_count < request.min_samples:
        return PerformanceDriftResponse(
            run_id=run_id,
            status="insufficient_data",
            sample_count=sample_count,
            calibration_buckets=[],
            false_positive_rate=None,
            win_rate=None,
            average_realized_r=None,
            confidence_error=None,
            affected_models=[],
            affected_strategies=[],
            recommended_actions=["collect_more_data"],
            blockers=[f"Insufficient samples: {sample_count} < {request.min_samples}"],
            warnings=["Need more labeled outcomes for reliable drift detection"],
            checked_at=checked_at,
        )
    
    # Compute calibration buckets
    calibration_buckets = _compute_calibration_buckets(entries)
    
    # Compute metrics
    wins = sum(1 for e, _ in entries if e.outcome_label == "win")
    losses = sum(1 for e, _ in entries if e.outcome_label == "loss")
    breakeven = sum(1 for e, _ in entries if e.outcome_label == "breakeven")
    
    win_rate = wins / (wins + losses) if (wins + losses) > 0 else None
    
    realized_rs = [e.realized_r for e, _ in entries if e.realized_r is not None]
    average_realized_r = sum(realized_rs) / len(realized_rs) if realized_rs else None
    
    false_positive_rate = _compute_false_positive_rate(entries)
    confidence_error = _compute_confidence_error(entries)
    
    # Determine status
    warnings = []
    
    # Check for significant calibration error
    high_calibration_error = any(
        b.calibration_error > 0.25 and b.count >= 3 
        for b in calibration_buckets
    )
    
    # Check for poor performance
    poor_performance = win_rate is not None and win_rate < 0.4 and (wins + losses) >= 10
    high_false_positive = false_positive_rate is not None and false_positive_rate > 0.5
    
    if poor_performance or high_calibration_error or high_false_positive:
        status: Literal["pass", "warn", "fail", "insufficient_data"] = "fail"
    elif (win_rate is not None and win_rate < 0.5) or (false_positive_rate is not None and false_positive_rate > 0.3):
        status = "warn"
    else:
        status = "pass"
    
    # Determine affected models and strategies
    affected_models = list(set(
        model 
        for _, request in entries 
        for model in request.model_stack
    ))
    
    affected_strategies = list(set(
        request.strategy_key 
        for _, request in entries 
        if request.strategy_key
    ))
    
    # Determine recommended actions
    recommended_actions = _determine_recommended_actions(
        status,
        sample_count,
        calibration_buckets,
        false_positive_rate,
        win_rate,
        affected_models,
        affected_strategies,
    )
    
    response = PerformanceDriftResponse(
        run_id=run_id,
        status=status,
        sample_count=sample_count,
        calibration_buckets=calibration_buckets,
        false_positive_rate=false_positive_rate,
        win_rate=win_rate,
        average_realized_r=average_realized_r,
        confidence_error=confidence_error,
        affected_models=affected_models,
        affected_strategies=affected_strategies,
        recommended_actions=recommended_actions,
        blockers=[],
        warnings=warnings,
        checked_at=checked_at,
    )
    
    # Store
    global _LATEST_DRIFT_CHECK, _DRIFT_HISTORY
    _LATEST_DRIFT_CHECK = response
    _DRIFT_HISTORY.append(response)
    save_performance_drift_run({**response.model_dump(mode="json"), "lookback_days": request.lookback_days, "strategy_key": request.strategy_key, "model_name": request.model_name})
    
    # Keep only last 100
    if len(_DRIFT_HISTORY) > 100:
        _DRIFT_HISTORY = _DRIFT_HISTORY[-100:]
    
    return response


def get_latest_drift_check() -> PerformanceDriftResponse | None:
    """Get the latest drift check."""
    row = get_latest_performance_drift_run()
    if row:
        restored = _drift_from_record(row)
        if restored:
            return restored
    return _LATEST_DRIFT_CHECK


def list_drift_history(limit: int = 20) -> list[PerformanceDriftResponse]:
    """List recent drift checks."""
    rows = list_performance_drift_runs(limit)
    restored = [_drift_from_record(row) for row in rows]
    db_runs = [run for run in restored if run is not None]
    if db_runs:
        return db_runs
    return _DRIFT_HISTORY[-limit:]
