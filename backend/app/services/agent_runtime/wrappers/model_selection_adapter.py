from __future__ import annotations

from typing import Any

from app.services.model_orchestrator_service import ModelRunRequest, run_model_orchestrator
from app.services.model_registry_service import get_model
from app.services.model_evidence.models import ModelEvidenceCreate
from app.services.model_evidence.service import save_model_evidence


def select_models(*, symbol: str, asset_class: str, horizon: str, strategy_key: str | None) -> dict[str, Any]:
    """Use existing model orchestrator + registry and persist model evidence records."""
    req = ModelRunRequest(
        symbols=[symbol.upper()],
        asset_class=asset_class,
        horizon="day_trade" if horizon in {"day_trading", "day_trade"} else horizon,
        source="auto",
        strategy_key=strategy_key,
        selected_models=None,
        feature_rows=None,
    )
    resp = run_model_orchestrator(req)

    # Persist evidence for completed + blocked + not_trained at least
    for bucket_name in ["completed_models", "blocked_models", "not_trained_models", "skipped_models"]:
        for item in resp.model_dump().get(bucket_name, []) or []:
            mk = item.get("model_key") or item.get("model") or "unknown"
            entry = get_model(mk) or get_model("weighted_ranker_v1")
            save_model_evidence(
                ModelEvidenceCreate(
                    model_key=mk,
                    model_name=item.get("model_name") or item.get("model") or (entry.display_name if entry else mk),
                    model_family=str(getattr(entry, "type", "unknown")) if entry else "unknown",
                    asset_class=asset_class,
                    horizon=horizon,
                    status=str(item.get("status") or bucket_name),
                    score=item.get("rank_score") or item.get("score"),
                    confidence=item.get("confidence"),
                    rank=item.get("rank"),
                    training_status="trained" if bool(getattr(entry, "trained_artifact_exists", False)) else "not_trained",
                    backtest_status=None,
                    paper_status=None,
                    qlib_artifact_id=None,
                    metrics={"bucket": bucket_name, "reason": item.get("reason") or item.get("next_step")},
                    blockers=[],
                    warnings=[],
                )
            )

    selected_model_keys = [m.get("model_key") or m.get("model") for m in (resp.completed_models or [])]
    selected_model_keys = [k for k in selected_model_keys if k]
    next_agent = "backtest_validation_agent" if selected_model_keys else "strategy_eligibility_agent"
    return {
        "selected_model_keys": selected_model_keys,
        "completed_models": resp.completed_models,
        "blocked_models": resp.blocked_models,
        "not_trained_models": resp.not_trained_models,
        "model_outputs": resp.model_outputs,
        "model_score_summary": {"completed_count": len(resp.completed_models or []), "blocked_count": len(resp.blocked_models or [])},
        "qlib_artifact_refs": [],
        "next_agent": next_agent,
        "next_action": "Proceed to backtest/proof validation." if next_agent == "backtest_validation_agent" else "Proceed to eligibility checks (no active model evidence).",
    }

