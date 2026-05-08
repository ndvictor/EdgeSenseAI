from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.services.model_registry_service import get_model_registry, get_model_eligibility
from app.services.qlib_integration.service import list_artifacts


class RankedModel(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_key: str
    display_name: str
    rank: int = 0
    model_score: float = Field(default=0.0, ge=0.0, le=100.0)
    status: Literal["selected", "eligible", "research_only", "blocked"] = "blocked"
    group: str
    provider: str
    reasons: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    latest_artifact_id: str | None = None
    latest_backtest_artifact_id: str | None = None
    latest_signal_artifact_id: str | None = None


class ModelRankerRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    workflow_run_id: str | None = None
    strategy_key: str | None = None
    horizon: str = "day_trading"
    asset_class: str = "stock"
    include_research_candidates: bool = True
    require_owner_approved_for_selection: bool = True


class ModelRankerResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    run_id: str
    status: Literal["completed", "partial", "blocked"]
    workflow_run_id: str | None = None
    strategy_key: str | None = None
    selected_model_key: str | None = None
    ranked_models: list[RankedModel]
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: str


_LATEST_MODEL_RANKING: ModelRankerResponse | None = None
_HISTORY: list[ModelRankerResponse] = []


def _latest_artifacts_by_model() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for artifact in list_artifacts(limit=200):
        if not artifact.model_key:
            continue
        bucket = out.setdefault(artifact.model_key, {})
        bucket.setdefault("latest_artifact_id", artifact.artifact_id)
        if artifact.artifact_type == "backtest":
            bucket.setdefault("latest_backtest_artifact_id", artifact.artifact_id)
        if artifact.artifact_type == "signal_scores":
            bucket.setdefault("latest_signal_artifact_id", artifact.artifact_id)
    return out


def _score_model(entry: dict[str, Any], artifact_ids: dict[str, str], request: ModelRankerRequest) -> tuple[float, str, list[str], list[str], list[str]]:
    reasons: list[str] = []
    warnings: list[str] = []
    blockers: list[str] = []
    score = 0.0

    model_key = str(entry.get("model_key"))
    eligibility = get_model_eligibility(model_key)
    group = str(entry.get("group") or "")

    if eligibility.get("eligible_for_active_scoring"):
        score += 70
        reasons.append("eligible_for_active_scoring")
        status = "eligible"
    elif bool(entry.get("allowed_for_research_backtesting")) and request.include_research_candidates:
        score += 35
        warnings.append("research_candidate_not_active_scoring")
        status = "research_only"
    else:
        status = "blocked"
        blockers.append(str(eligibility.get("blocked_reason") or "model_not_eligible"))

    if bool(entry.get("trained_artifact_exists")):
        score += 8
        reasons.append("trained_artifact_exists")
    if bool(entry.get("evaluation_passed")):
        score += 8
        reasons.append("evaluation_passed")
    if bool(entry.get("calibration_passed")):
        score += 5
        reasons.append("calibration_passed")
    if bool(entry.get("owner_approved")):
        score += 5
        reasons.append("owner_approved")
    elif request.require_owner_approved_for_selection and status == "eligible":
        status = "blocked"
        blockers.append("owner_approval_missing")

    if artifact_ids.get("latest_backtest_artifact_id"):
        score += 3
        reasons.append("qlib_backtest_artifact_available")
    if artifact_ids.get("latest_signal_artifact_id"):
        score += 1
        reasons.append("qlib_signal_artifact_available")

    if group.startswith("candidate") and status == "research_only":
        warnings.append("candidate_model_not_allowed_for_final_decision")

    return min(100.0, score), status, reasons, blockers, warnings


def run_model_ranker(request: ModelRankerRequest) -> ModelRankerResponse:
    global _LATEST_MODEL_RANKING

    registry = get_model_registry()
    artifacts = _latest_artifacts_by_model()
    ranked: list[RankedModel] = []

    for entry in registry.get("models", []):
        model_key = str(entry.get("model_key"))
        artifact_ids = artifacts.get(model_key, {})
        score, status, reasons, blockers, warnings = _score_model(entry, artifact_ids, request)
        ranked.append(
            RankedModel(
                model_key=model_key,
                display_name=str(entry.get("display_name") or model_key),
                model_score=score,
                status=status,  # type: ignore[arg-type]
                group=str(entry.get("group") or "unknown"),
                provider=str(entry.get("provider") or "internal"),
                reasons=reasons,
                blockers=blockers,
                warnings=warnings,
                latest_artifact_id=artifact_ids.get("latest_artifact_id"),
                latest_backtest_artifact_id=artifact_ids.get("latest_backtest_artifact_id"),
                latest_signal_artifact_id=artifact_ids.get("latest_signal_artifact_id"),
            )
        )

    ranked.sort(key=lambda m: m.model_score, reverse=True)
    selected_model_key: str | None = None
    for idx, item in enumerate(ranked, start=1):
        item.rank = idx
        if selected_model_key is None and item.status in {"eligible", "selected"}:
            item.status = "selected"
            selected_model_key = item.model_key

    blockers = [] if selected_model_key else ["no_model_eligible_for_active_scoring"]
    resp = ModelRankerResponse(
        run_id=f"model-rank-{uuid4().hex[:12]}",
        status="completed" if selected_model_key else "partial" if ranked else "blocked",
        workflow_run_id=request.workflow_run_id,
        strategy_key=request.strategy_key,
        selected_model_key=selected_model_key,
        ranked_models=ranked,
        blockers=blockers,
        warnings=sorted({w for r in ranked for w in r.warnings}),
        created_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    )
    _LATEST_MODEL_RANKING = resp
    _HISTORY.append(resp)
    if len(_HISTORY) > 100:
        del _HISTORY[:-100]
    return resp


def get_latest_model_ranking() -> ModelRankerResponse | None:
    return _LATEST_MODEL_RANKING


def list_model_ranking_history(limit: int = 20) -> list[ModelRankerResponse]:
    return _HISTORY[-limit:]
