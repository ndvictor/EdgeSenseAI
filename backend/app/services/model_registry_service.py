from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ModelGroup = Literal[
    "active_working_models",
    "candidate_open_source_models",
    "candidate_pretrained_models",
    "candidate_statistical_models",
    "untrained_internal_models",
    "blocked_models",
]


class ModelRegistryEntry(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_key: str
    display_name: str
    group: ModelGroup
    type: str
    provider: str = "internal"
    status: str
    use_case: list[str] = Field(default_factory=list)
    allowed_for_live_scoring: bool = False
    allowed_for_research_backtesting: bool = False
    allowed_for_final_trade_decision: bool = False
    requires_trained_artifact: bool = False
    trained_artifact_exists: bool = False
    evaluation_passed: bool = False
    calibration_passed: bool = False
    owner_approved: bool = False
    requires_news_text_input: bool = False
    requires_options_data: bool = False
    requires_market_data: bool = True
    requires_feature_store: bool = False
    requires_risk_gate: bool = True
    requires_human_approval: bool = True
    blocked_reason: str | None = None
    next_action: str = "Review model registry status before use."
    artifact_path: str | None = None
    evaluation_notes: str | None = None
    cost_profile: Literal["free", "local_compute", "paid_api_possible"] = "free"
    safety_notes: list[str] = Field(default_factory=list)


def _entry(**kwargs: Any) -> ModelRegistryEntry:
    if kwargs.get("allowed_for_final_trade_decision") is True:
        raise ValueError("No model may be registered as allowed_for_final_trade_decision=true")
    return ModelRegistryEntry(**kwargs)


_MODEL_REGISTRY: dict[str, ModelRegistryEntry] = {
    "weighted_ranker_v1": _entry(
        model_key="weighted_ranker_v1",
        display_name="Weighted Ranker V1",
        group="active_working_models",
        type="deterministic_statistical_baseline",
        provider="internal",
        status="active",
        use_case=["research/paper candidate scoring", "deterministic baseline", "model tournament benchmark"],
        allowed_for_live_scoring=True,
        allowed_for_research_backtesting=True,
        allowed_for_final_trade_decision=False,
        requires_trained_artifact=False,
        trained_artifact_exists=True,
        evaluation_passed=True,
        calibration_passed=True,
        owner_approved=True,
        requires_feature_store=True,
        requires_risk_gate=True,
        requires_human_approval=True,
        next_action="Use as active baseline, then pass outputs through risk gate and human approval.",
        evaluation_notes="Active deterministic baseline only; not a final trade decision engine.",
        cost_profile="free",
        safety_notes=["Research/paper scoring only", "Risk gate required", "Human approval required", "Cannot make final trade decisions"],
    ),
    "xgboost_ranker": _entry(
        model_key="xgboost_ranker",
        display_name="XGBoost Ranker",
        group="untrained_internal_models",
        type="supervised_ranker",
        provider="internal",
        status="not_trained",
        use_case=["future supervised candidate ranking after labeled outcomes exist"],
        allowed_for_live_scoring=False,
        allowed_for_research_backtesting=True,
        allowed_for_final_trade_decision=False,
        requires_trained_artifact=True,
        trained_artifact_exists=False,
        evaluation_passed=False,
        calibration_passed=False,
        owner_approved=False,
        requires_feature_store=True,
        blocked_reason="No trained/evaluated/calibrated/approved artifact exists.",
        next_action="Collect labeled outcomes, train artifact, walk-forward evaluate, calibrate, then request owner approval.",
        cost_profile="local_compute",
        safety_notes=["Not trained", "Does not influence scoring", "Must not be selected for active scoring"],
    ),
    "qlib_research_platform": _entry(
        model_key="qlib_research_platform",
        display_name="Qlib Research Platform",
        group="candidate_open_source_models",
        type="open_source_quant_research_platform",
        provider="Microsoft Qlib",
        status="candidate",
        use_case=["research lab", "model comparison", "strategy backtesting", "supervised ML experiments", "model tournament"],
        allowed_for_live_scoring=False,
        allowed_for_research_backtesting=True,
        allowed_for_final_trade_decision=False,
        blocked_reason="Research platform candidate; wrapper/evaluation/approval not wired for active scoring.",
        next_action="Evaluate as research/backtesting integration, not active scoring.",
        cost_profile="local_compute",
        safety_notes=["Research candidate only", "No prediction output in production workflow"],
    ),
    "vectorbt_backtrader": _entry(
        model_key="vectorbt_backtrader",
        display_name="vectorbt / backtrader",
        group="candidate_open_source_models",
        type="backtesting_engine",
        provider="open_source",
        status="candidate",
        use_case=["strategy backtesting", "parameter testing", "walk-forward testing"],
        allowed_for_live_scoring=False,
        allowed_for_research_backtesting=True,
        allowed_for_final_trade_decision=False,
        blocked_reason="Backtesting engine candidate; not a live scoring model.",
        next_action="Use for research/backtest job execution only.",
        cost_profile="local_compute",
        safety_notes=["Backtesting only", "Does not create predictions for active scoring"],
    ),
    "river_online_models": _entry(
        model_key="river_online_models",
        display_name="River Online Models",
        group="candidate_open_source_models",
        type="online_learning",
        provider="River open-source",
        status="candidate",
        use_case=["lightweight adaptive models", "drift-aware streaming learning"],
        allowed_for_live_scoring=False,
        allowed_for_research_backtesting=True,
        allowed_for_final_trade_decision=False,
        blocked_reason="Candidate until wrapper, evaluation, calibration, and owner approval exist.",
        next_action="Prototype offline/streaming research wrapper before active scoring.",
        cost_profile="local_compute",
        safety_notes=["Candidate only", "No active scoring until evaluated"],
    ),
    "chronos_bolt_tiny": _entry(
        model_key="chronos_bolt_tiny",
        display_name="Chronos-Bolt Tiny",
        group="candidate_pretrained_models",
        type="pretrained_time_series_forecasting",
        provider="Amazon Chronos",
        status="candidate",
        use_case=["probabilistic forecast benchmark", "price/volume forecast", "anomaly context", "directional sanity check"],
        allowed_for_live_scoring=False,
        allowed_for_research_backtesting=True,
        allowed_for_final_trade_decision=False,
        blocked_reason="Pretrained candidate until wrapper and evaluation exist.",
        next_action="Add research wrapper and benchmark against weighted_ranker_v1 before active scoring consideration.",
        cost_profile="local_compute",
        safety_notes=["Research candidate only", "Forecast output cannot make final trade decisions"],
    ),
    "chronos_bolt_mini": _entry(
        model_key="chronos_bolt_mini",
        display_name="Chronos-Bolt Mini",
        group="candidate_pretrained_models",
        type="pretrained_time_series_forecasting",
        provider="Amazon Chronos",
        status="candidate",
        use_case=["probabilistic forecast benchmark", "price/volume forecast", "anomaly context", "directional sanity check"],
        allowed_for_live_scoring=False,
        allowed_for_research_backtesting=True,
        allowed_for_final_trade_decision=False,
        blocked_reason="Pretrained candidate until wrapper and evaluation exist.",
        next_action="Add research wrapper and benchmark before active scoring consideration.",
        cost_profile="local_compute",
        safety_notes=["Research candidate only", "Potentially heavier than tiny variant"],
    ),
    "finbert_sentiment": _entry(
        model_key="finbert_sentiment",
        display_name="FinBERT Sentiment",
        group="candidate_pretrained_models",
        type="financial_nlp_sentiment",
        provider="Hugging Face/local model",
        status="candidate",
        use_case=["news sentiment", "earnings/catalyst score", "macro event interpretation"],
        allowed_for_live_scoring=False,
        allowed_for_research_backtesting=True,
        allowed_for_final_trade_decision=False,
        requires_news_text_input=True,
        requires_market_data=False,
        blocked_reason="Requires news pipeline, wrapper, evaluation, and owner approval.",
        next_action="Wire news text pipeline and evaluate sentiment usefulness before activation.",
        cost_profile="local_compute",
        safety_notes=["Requires news text", "Sentiment is context only, not final decision"],
    ),
    "statsmodels_arimax_var": _entry(
        model_key="statsmodels_arimax_var",
        display_name="statsmodels ARIMAX/VAR",
        group="candidate_statistical_models",
        type="classical_statistical_forecast",
        provider="statsmodels",
        status="candidate",
        use_case=["ARIMAX/VAR baseline", "macro/time-series relationship testing"],
        allowed_for_live_scoring=False,
        allowed_for_research_backtesting=True,
        allowed_for_final_trade_decision=False,
        blocked_reason="Requires wrapper and evaluation before active scoring.",
        next_action="Implement research wrapper and compare to baseline.",
        cost_profile="local_compute",
        safety_notes=["Research candidate only"],
    ),
    "garch_egarch_volatility": _entry(
        model_key="garch_egarch_volatility",
        display_name="GARCH/EGARCH Volatility",
        group="candidate_statistical_models",
        type="volatility_forecast",
        provider="arch/statsmodels-style implementation",
        status="candidate",
        use_case=["volatility forecast", "risk sizing", "stop distance", "strategy selection"],
        allowed_for_live_scoring=False,
        allowed_for_research_backtesting=True,
        allowed_for_final_trade_decision=False,
        blocked_reason="Requires wrapper and evaluation before active scoring.",
        next_action="Prototype volatility research wrapper and validate risk-sizing value.",
        cost_profile="local_compute",
        safety_notes=["Can inform research/risk after evaluation only"],
    ),
    "hmm_regime": _entry(
        model_key="hmm_regime",
        display_name="HMM Regime",
        group="candidate_statistical_models",
        type="regime_classification",
        provider="hmmlearn/custom",
        status="candidate",
        use_case=["hidden market state classification", "trend/chop/volatility state"],
        allowed_for_live_scoring=False,
        allowed_for_research_backtesting=True,
        allowed_for_final_trade_decision=False,
        blocked_reason="Requires wrapper and evaluation before active scoring.",
        next_action="Research HMM regime wrapper and compare to deterministic regime baseline.",
        cost_profile="local_compute",
        safety_notes=["Research candidate only"],
    ),
    "kalman_trend_filter": _entry(
        model_key="kalman_trend_filter",
        display_name="Kalman Trend Filter",
        group="candidate_statistical_models",
        type="classical_filtering",
        provider="custom/statsmodels-style",
        status="candidate",
        use_case=["adaptive trend/mean reversion signal"],
        allowed_for_live_scoring=False,
        allowed_for_research_backtesting=True,
        allowed_for_final_trade_decision=False,
        blocked_reason="Requires wrapper and evaluation before active scoring.",
        next_action="Prototype trend-filter research wrapper and compare with VWAP/momentum baseline.",
        cost_profile="local_compute",
        safety_notes=["Research candidate only"],
    ),
}


def get_model_registry() -> dict[str, Any]:
    models = [entry.model_dump() for entry in _MODEL_REGISTRY.values()]
    groups = {group: [entry.model_dump() for entry in _MODEL_REGISTRY.values() if entry.group == group] for group in _group_names()}
    return {
        "data_source": "static_governed_registry",
        "groups": groups,
        "models": models,
        "active_model_count": len(groups["active_working_models"]),
        "candidate_model_count": sum(len(groups[group]) for group in ["candidate_open_source_models", "candidate_pretrained_models", "candidate_statistical_models"]),
        "untrained_internal_model_count": len(groups["untrained_internal_models"]),
        "blocked_model_count": len(groups["blocked_models"]),
        "final_trade_decision_models_count": len([entry for entry in _MODEL_REGISTRY.values() if entry.allowed_for_final_trade_decision]),
        "safety_notes": [
            "weighted_ranker_v1 is the only active scoring baseline",
            "xgboost_ranker is not trained and does not influence scoring",
            "external/pretrained/statistical models are research candidates only",
            "no model may make final trade decisions",
        ],
    }


def _group_names() -> list[ModelGroup]:
    return [
        "active_working_models",
        "candidate_open_source_models",
        "candidate_pretrained_models",
        "candidate_statistical_models",
        "untrained_internal_models",
        "blocked_models",
    ]


def get_model_registry_groups() -> dict[str, Any]:
    return {"groups": _group_names(), "data_source": "static_governed_registry"}


def get_models_by_group(group: str) -> list[dict[str, Any]]:
    return [entry.model_dump() for entry in _MODEL_REGISTRY.values() if entry.group == group]


def get_active_working_models() -> list[dict[str, Any]]:
    return get_models_by_group("active_working_models")


def get_candidate_models() -> dict[str, list[dict[str, Any]]]:
    return {
        "candidate_open_source_models": get_models_by_group("candidate_open_source_models"),
        "candidate_pretrained_models": get_models_by_group("candidate_pretrained_models"),
        "candidate_statistical_models": get_models_by_group("candidate_statistical_models"),
    }


def get_untrained_internal_models() -> list[dict[str, Any]]:
    return get_models_by_group("untrained_internal_models")


def get_blocked_models() -> list[dict[str, Any]]:
    return get_models_by_group("blocked_models")


def get_model(model_key: str) -> ModelRegistryEntry | None:
    return _MODEL_REGISTRY.get(_normalize_model_key(model_key))


def _normalize_model_key(model_key: str) -> str:
    if model_key == "weighted_ranker":
        return "weighted_ranker_v1"
    return model_key


def is_model_eligible_for_active_scoring(model_key: str) -> bool:
    entry = get_model(model_key)
    if not entry:
        return False
    if entry.allowed_for_final_trade_decision:
        return False
    if entry.model_key == "weighted_ranker_v1":
        return True
    if entry.model_key == "xgboost_ranker":
        return all([
            entry.trained_artifact_exists,
            entry.evaluation_passed,
            entry.calibration_passed,
            entry.owner_approved,
            entry.allowed_for_live_scoring,
        ])
    return all([
        entry.allowed_for_live_scoring,
        entry.trained_artifact_exists or not entry.requires_trained_artifact,
        entry.evaluation_passed,
        entry.calibration_passed,
        entry.owner_approved,
    ])


def get_model_eligibility(model_key: str) -> dict[str, Any]:
    entry = get_model(model_key)
    if not entry:
        return {
            "model_key": model_key,
            "eligible_for_active_scoring": False,
            "reason": "Model is not registered.",
            "next_action": "Add model to registry before use.",
        }
    eligible = is_model_eligible_for_active_scoring(model_key)
    missing: list[str] = []
    if entry.requires_trained_artifact and not entry.trained_artifact_exists:
        missing.append("trained_artifact_exists")
    if not entry.evaluation_passed:
        missing.append("evaluation_passed")
    if not entry.calibration_passed:
        missing.append("calibration_passed")
    if not entry.owner_approved:
        missing.append("owner_approved")
    if not entry.allowed_for_live_scoring:
        missing.append("allowed_for_live_scoring")
    if entry.allowed_for_final_trade_decision:
        missing.append("allowed_for_final_trade_decision_must_be_false")
    return {
        "model_key": entry.model_key,
        "display_name": entry.display_name,
        "group": entry.group,
        "status": entry.status,
        "eligible_for_active_scoring": eligible,
        "missing_requirements": [] if eligible else missing,
        "blocked_reason": None if eligible else (entry.blocked_reason or "Eligibility requirements are not met."),
        "next_action": entry.next_action,
        "safety_notes": entry.safety_notes,
    }


def get_model_selection_summary() -> dict[str, Any]:
    return {
        "active_models": get_active_working_models(),
        "candidate_models": get_candidate_models(),
        "untrained_internal_models": get_untrained_internal_models(),
        "blocked_models": get_blocked_models(),
        "eligible_active_scoring_models": [entry.model_dump() for entry in _MODEL_REGISTRY.values() if is_model_eligible_for_active_scoring(entry.model_key)],
        "xgboost_eligibility": get_model_eligibility("xgboost_ranker"),
        "product_truth": {
            "weighted_ranker_v1_active_baseline": is_model_eligible_for_active_scoring("weighted_ranker_v1"),
            "xgboost_ranker_not_active": not is_model_eligible_for_active_scoring("xgboost_ranker"),
            "candidate_models_research_only": True,
            "no_model_final_trade_decision": all(not entry.allowed_for_final_trade_decision for entry in _MODEL_REGISTRY.values()),
        },
    }


def skipped_model_record(model_key: str, status: str | None = None) -> dict[str, Any]:
    entry = get_model(model_key)
    if not entry:
        return {
            "model": model_key,
            "model_name": model_key,
            "status": status or "not_registered",
            "reason": "Model is not registered in the governed model registry.",
            "next_step": "Register and evaluate model before use.",
            "data_source": "model_registry",
        }
    return {
        "model": entry.model_key,
        "model_name": entry.display_name,
        "status": status or ("not_trained" if entry.model_key == "xgboost_ranker" else "candidate_not_active"),
        "reason": entry.blocked_reason or "Model is not eligible for active scoring.",
        "needed_inputs": get_model_eligibility(entry.model_key).get("missing_requirements", []),
        "next_step": entry.next_action,
        "data_source": "model_registry",
        "group": entry.group,
        "allowed_for_research_backtesting": entry.allowed_for_research_backtesting,
        "allowed_for_final_trade_decision": entry.allowed_for_final_trade_decision,
    }
