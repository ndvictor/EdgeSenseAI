"""Research Priority Agent Service.

Creates prioritized research/backtest/model-improvement tasks from journal outcomes, 
drift checks, false positives, risk rejects, and no-trade decisions.

NO LLM calls.
Deterministic scoring from evidence.
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.services.persistence_service import (
    get_latest_research_priority_run,
    list_research_priority_runs,
    save_research_priority_run,
)
from app.services.journal_outcome_service import (
    _JOURNAL_CREATE_REQUESTS,
    _JOURNAL_ENTRIES,
)
from app.services.performance_drift_service import (
    _LATEST_DRIFT_CHECK,
)


class ResearchTask(BaseModel):
    """A research task."""

    model_config = ConfigDict(protected_namespaces=())

    task_id: str
    priority_rank: int
    priority_score: float = Field(..., ge=0, le=100)
    task_type: Literal["backtest", "model_evaluation", "strategy_review", "feature_review", "risk_filter_review", "data_quality_review", "retraining_request"]
    title: str
    description: str
    linked_strategy_key: str | None = None
    linked_model: str | None = None
    evidence: list[str] = Field(default_factory=list)
    suggested_next_step: str
    status: Literal["open", "in_progress", "completed", "rejected"] = "open"


class ResearchPriorityRequest(BaseModel):
    """Request to generate research priorities."""

    model_config = ConfigDict(protected_namespaces=())

    lookback_days: int = Field(default=30, ge=1)
    include_drift: bool = True
    include_journal: bool = True
    include_no_trade: bool = True
    include_recommendation_rejects: bool = True
    max_tasks: int = Field(default=20, ge=1)


class ResearchPriorityResponse(BaseModel):
    """Response with research priorities."""

    model_config = ConfigDict(protected_namespaces=())

    run_id: str
    status: Literal["generated", "insufficient_evidence", "empty"]
    tasks: list[ResearchTask]
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime


# In-memory storage
_LATEST_RESEARCH_PRIORITY: ResearchPriorityResponse | None = None
_RESEARCH_HISTORY: list[ResearchPriorityResponse] = []


def _research_from_record(row: dict) -> ResearchPriorityResponse | None:
    try:
        return ResearchPriorityResponse.model_validate({
            "run_id": row.get("run_id"),
            "status": row.get("status"),
            "tasks": row.get("tasks") or [],
            "blockers": row.get("blockers") or [],
            "warnings": row.get("warnings") or [],
            "created_at": row.get("created_at"),
        })
    except Exception:
        return None


def _collect_evidence(
    lookback_days: int,
    include_drift: bool,
    include_journal: bool,
    include_no_trade: bool,
) -> dict[str, Any]:
    """Collect evidence from various sources."""
    now = datetime.now(timezone.utc)
    
    evidence = {
        "drift_findings": [],
        "journal_outcomes": [],
        "no_trade_decisions": [],
        "strategies_with_issues": set(),
        "models_with_issues": set(),
    }
    
    # Collect from drift check
    if include_drift and _LATEST_DRIFT_CHECK:
        drift = _LATEST_DRIFT_CHECK
        if drift.status in ("warn", "fail"):
            evidence["drift_findings"].append({
                "type": "drift",
                "status": drift.status,
                "sample_count": drift.sample_count,
                "win_rate": drift.win_rate,
                "false_positive_rate": drift.false_positive_rate,
                "recommended_actions": drift.recommended_actions,
            })
            evidence["strategies_with_issues"].update(drift.affected_strategies)
            evidence["models_with_issues"].update(drift.affected_models)
    
    # Collect from journal entries
    if include_journal:
        for entry_id, entry in _JOURNAL_ENTRIES.items():
            # Check lookback
            days_old = (now - entry.created_at).days
            if days_old > lookback_days:
                continue
            
            request = _JOURNAL_CREATE_REQUESTS.get(entry_id)
            
            # Add to appropriate evidence bucket
            if entry.source_type == "no_trade":
                evidence["no_trade_decisions"].append({
                    "symbol": entry.symbol,
                    "outcome_label": entry.outcome_label,
                    "lessons": entry.lessons,
                })
            else:
                evidence["journal_outcomes"].append({
                    "symbol": entry.symbol,
                    "outcome_label": entry.outcome_label,
                    "realized_r": entry.realized_r,
                    "strategy_key": request.strategy_key if request else None,
                    "lessons": entry.lessons,
                })
                
                # Track strategies with issues
                if entry.outcome_label == "loss" and request and request.strategy_key:
                    evidence["strategies_with_issues"].add(request.strategy_key)
                
                # Track models with issues
                if entry.confidence_error is not None and entry.confidence_error > 0.5 and request:
                    for model in request.model_stack:
                        evidence["models_with_issues"].add(model)
    
    return evidence


def _score_task_priority(
    task_type: str,
    evidence_count: int,
    severity: str,
) -> float:
    """Score task priority 0-100."""
    base_score = 50.0
    
    # Type weighting
    type_weights = {
        "retraining_request": 20,
        "risk_filter_review": 15,
        "model_evaluation": 10,
        "strategy_review": 10,
        "feature_review": 5,
        "backtest": 5,
        "data_quality_review": 3,
    }
    base_score += type_weights.get(task_type, 0)
    
    # Evidence weighting
    base_score += min(evidence_count * 5, 20)  # Cap at 20
    
    # Severity weighting
    severity_weights = {
        "high": 20,
        "medium": 10,
        "low": 0,
    }
    base_score += severity_weights.get(severity, 0)
    
    return min(100, max(0, base_score))


def _generate_tasks_from_evidence(
    evidence: dict[str, Any],
    max_tasks: int,
) -> list[ResearchTask]:
    """Generate research tasks from collected evidence."""
    tasks = []
    task_counter = 0
    
    # Tasks from drift findings
    for drift in evidence["drift_findings"]:
        if "collect_more_data" in drift.get("recommended_actions", []):
            task_counter += 1
            tasks.append(ResearchTask(
                task_id=f"task-{uuid4().hex[:8]}",
                priority_rank=task_counter,
                priority_score=_score_task_priority("backtest", drift["sample_count"], "medium"),
                task_type="backtest",
                title="Collect More Outcome Labels",
                description=f"Drift check shows {drift['sample_count']} samples. Need more labeled outcomes for reliable calibration.",
                evidence=[f"Drift status: {drift['status']}", f"Sample count: {drift['sample_count']}"],
                suggested_next_step="Run more paper trades and label outcomes",
            ))
        
        if "retrain_model" in drift.get("recommended_actions", []):
            for model in evidence["models_with_issues"]:
                task_counter += 1
                tasks.append(ResearchTask(
                    task_id=f"task-{uuid4().hex[:8]}",
                    priority_rank=task_counter,
                    priority_score=_score_task_priority("retraining_request", 1, "high"),
                    task_type="retraining_request",
                    title=f"Retrain Model: {model}",
                    description=f"Model {model} shows calibration error. Consider retraining with recent data.",
                    linked_model=model,
                    evidence=[f"Drift status: {drift['status']}"],
                    suggested_next_step="Review model features and retrain",
                ))
        
        if "pause_strategy" in drift.get("recommended_actions", []):
            for strategy in evidence["strategies_with_issues"]:
                task_counter += 1
                tasks.append(ResearchTask(
                    task_id=f"task-{uuid4().hex[:8]}",
                    priority_rank=task_counter,
                    priority_score=_score_task_priority("strategy_review", 1, "high"),
                    task_type="strategy_review",
                    title=f"Review Strategy: {strategy}",
                    description=f"Strategy {strategy} shows poor win rate. Review strategy rules and market fit.",
                    linked_strategy_key=strategy,
                    evidence=[f"Win rate below threshold"],
                    suggested_next_step="Analyze recent trades and market conditions",
                ))
        
        if "reduce_weight" in drift.get("recommended_actions", []):
            for strategy in evidence["strategies_with_issues"]:
                task_counter += 1
                tasks.append(ResearchTask(
                    task_id=f"task-{uuid4().hex[:8]}",
                    priority_rank=task_counter,
                    priority_score=_score_task_priority("strategy_review", 1, "medium"),
                    task_type="strategy_review",
                    title=f"Reduce Strategy Weight: {strategy}",
                    description=f"Strategy {strategy} performance degraded. Consider reducing meta-model weight.",
                    linked_strategy_key=strategy,
                    evidence=[f"Win rate below 50%", f"False positive rate elevated"],
                    suggested_next_step="Reduce weight and monitor",
                ))
    
    # Tasks from no-trade decisions
    no_trade_with_lessons = [d for d in evidence["no_trade_decisions"] if d.get("lessons")]
    if no_trade_with_lessons:
        task_counter += 1
        tasks.append(ResearchTask(
            task_id=f"task-{uuid4().hex[:8]}",
            priority_rank=task_counter,
            priority_score=_score_task_priority("strategy_review", len(no_trade_with_lessons), "low"),
            task_type="strategy_review",
            title="Review No-Trade Decision Patterns",
            description=f"{len(no_trade_with_lessons)} no-trade decisions with lessons. Review patterns to improve signal quality.",
            evidence=[f"No-trade count: {len(evidence['no_trade_decisions'])}"],
            suggested_next_step="Analyze no-trade patterns and adjust filters",
        ))
    
    # Tasks from journal outcomes with lessons
    losses_with_lessons = [o for o in evidence["journal_outcomes"] if o["outcome_label"] == "loss" and o.get("lessons")]
    if losses_with_lessons:
        # Group by strategy
        by_strategy: dict[str, list] = {}
        for outcome in losses_with_lessons:
            strategy = outcome.get("strategy_key")
            if strategy:
                by_strategy.setdefault(strategy, []).append(outcome)
        
        for strategy, outcomes in by_strategy.items():
            task_counter += 1
            tasks.append(ResearchTask(
                task_id=f"task-{uuid4().hex[:8]}",
                priority_rank=task_counter,
                priority_score=_score_task_priority("risk_filter_review", len(outcomes), "medium"),
                task_type="risk_filter_review",
                title=f"Review Risk Filters: {strategy}",
                description=f"{len(outcomes)} losses with lessons for strategy {strategy}. Review stop placement and position sizing.",
                linked_strategy_key=strategy,
                evidence=[f"Losses: {len(outcomes)}"],
                suggested_next_step="Analyze loss patterns and adjust risk parameters",
            ))
    
    # If no specific tasks, create general collection task
    if not tasks and evidence["journal_outcomes"]:
        task_counter += 1
        tasks.append(ResearchTask(
            task_id=f"task-{uuid4().hex[:8]}",
            priority_rank=task_counter,
            priority_score=_score_task_priority("backtest", len(evidence["journal_outcomes"]), "low"),
            task_type="backtest",
            title="Continue Outcome Collection",
            description=f"{len(evidence['journal_outcomes'])} outcomes recorded. Continue collecting to build statistical significance.",
            evidence=[f"Total outcomes: {len(evidence['journal_outcomes'])}"],
            suggested_next_step="Label more paper trade outcomes",
        ))
    
    # Sort by priority score desc
    tasks.sort(key=lambda t: t.priority_score, reverse=True)
    
    # Re-rank
    for i, task in enumerate(tasks, 1):
        task.priority_rank = i
    
    # Limit
    return tasks[:max_tasks]


def generate_research_priorities(request: ResearchPriorityRequest) -> ResearchPriorityResponse:
    """Generate research priorities from evidence.
    
    Rules:
    - If insufficient evidence, return collect-more-data tasks
    - No LLM calls
    - Deterministic scoring
    """
    run_id = f"research-{uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc)
    
    # Collect evidence
    evidence = _collect_evidence(
        request.lookback_days,
        request.include_drift,
        request.include_journal,
        request.include_no_trade,
    )
    
    # Check if we have enough evidence
    total_evidence = (
        len(evidence["drift_findings"]) +
        len(evidence["journal_outcomes"]) +
        len(evidence["no_trade_decisions"])
    )
    
    if total_evidence == 0:
        return ResearchPriorityResponse(
            run_id=run_id,
            status="insufficient_evidence",
            tasks=[
                ResearchTask(
                    task_id=f"task-{uuid4().hex[:8]}",
                    priority_rank=1,
                    priority_score=100.0,
                    task_type="backtest",
                    title="Collect Initial Outcomes",
                    description="No journal entries or drift data available. Start by running paper trades and labeling outcomes.",
                    evidence=["No outcomes recorded"],
                    suggested_next_step="Run recommendation pipeline and create paper trades",
                )
            ],
            blockers=["No evidence available"],
            warnings=["Need to run paper trades and label outcomes first"],
            created_at=created_at,
        )
    
    # Generate tasks
    tasks = _generate_tasks_from_evidence(evidence, request.max_tasks)
    
    status: Literal["generated", "insufficient_evidence", "empty"] = "generated" if tasks else "empty"
    
    response = ResearchPriorityResponse(
        run_id=run_id,
        status=status,
        tasks=tasks,
        blockers=[],
        warnings=[],
        created_at=created_at,
    )
    
    # Store
    global _LATEST_RESEARCH_PRIORITY, _RESEARCH_HISTORY
    _LATEST_RESEARCH_PRIORITY = response
    _RESEARCH_HISTORY.append(response)
    save_research_priority_run(response)
    
    # Keep only last 100
    if len(_RESEARCH_HISTORY) > 100:
        _RESEARCH_HISTORY = _RESEARCH_HISTORY[-100:]
    
    return response


def get_latest_research_priority() -> ResearchPriorityResponse | None:
    """Get the latest research priority run."""
    row = get_latest_research_priority_run()
    if row:
        restored = _research_from_record(row)
        if restored:
            return restored
    return _LATEST_RESEARCH_PRIORITY


def list_research_history(limit: int = 20) -> list[ResearchPriorityResponse]:
    """List recent research priority runs."""
    rows = list_research_priority_runs(limit)
    restored = [_research_from_record(row) for row in rows]
    db_runs = [run for run in restored if run is not None]
    if db_runs:
        return db_runs
    return _RESEARCH_HISTORY[-limit:]


def get_open_tasks() -> list[ResearchTask]:
    """Get all open tasks from latest research priority."""
    latest = get_latest_research_priority()
    if latest is None:
        return []
    return [t for t in latest.tasks if t.status == "open"]


def update_task_status(task_id: str, status: str) -> ResearchTask | None:
    """Update task status."""
    if _LATEST_RESEARCH_PRIORITY is None:
        return None
    
    for task in _LATEST_RESEARCH_PRIORITY.tasks:
        if task.task_id == task_id:
            task.status = status  # type: ignore
            return task
    
    return None
