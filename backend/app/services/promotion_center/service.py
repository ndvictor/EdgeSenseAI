"""Read-only promotion readiness views built from registry + evidence records only.

No fabricated performance metrics: numeric fields come solely from evidence.metrics when present.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.services.model_evidence.models import ModelEvidenceOut
from app.services.model_evidence.service import list_model_evidence
from app.services.model_registry_service import get_model_registry
from app.services.strategy_evidence.models import StrategyEvidenceOut
from app.services.strategy_evidence.service import list_strategy_evidence
from app.strategies.registry import StrategyConfig, list_strategies


class StrategyPromotionRow(BaseModel):
    strategy_key: str
    display_name: str
    setup_type: str
    status: str
    sample_size: int | None = None
    avg_r: float | None = None
    profit_factor: float | None = None
    max_drawdown_r: float | None = None
    rule_violations: int | None = None
    spread_slippage_acceptable: bool | None = None
    small_account_feasible: bool | None = None
    promotion_readiness: Literal["not_ready", "eligible_for_review"]
    blockers: list[str] = Field(default_factory=list)
    next_action: str


class ModelPromotionRow(BaseModel):
    model_key: str
    model_role: str
    status: str
    allowed_strategy_keys: list[str] = Field(default_factory=list)
    sample_size: int | None = None
    validation_score: float | None = None
    calibration_status: str | None = None
    prediction_error_r: float | None = None
    promotion_readiness: Literal["not_ready", "eligible_for_review"]
    blockers: list[str] = Field(default_factory=list)
    next_action: str


class PromotionStrategiesResponse(BaseModel):
    status: Literal["ok"] = "ok"
    data_source: Literal["promotion_center_readonly_v1"] = "promotion_center_readonly_v1"
    strategies: list[StrategyPromotionRow]


class PromotionModelsResponse(BaseModel):
    status: Literal["ok"] = "ok"
    data_source: Literal["promotion_center_readonly_v1"] = "promotion_center_readonly_v1"
    models: list[ModelPromotionRow]


def _pick_metric(metrics: dict[str, Any], key: str) -> Any:
    if not metrics:
        return None
    return metrics.get(key)


def _strategy_thresholds_pass(metrics: dict[str, Any]) -> tuple[bool, list[str]]:
    """Returns (passes_all, failing_reasons). Missing keys fail the gate."""
    fails: list[str] = []
    if not metrics:
        return False, ["missing_evidence"]

    try:
        ss = int(_pick_metric(metrics, "sample_size") or 0)
        if ss < 50:
            fails.append("sample_size_below_50")
    except (TypeError, ValueError):
        fails.append("sample_size_invalid")

    try:
        ar = float(_pick_metric(metrics, "avg_r") if _pick_metric(metrics, "avg_r") is not None else float("nan"))
        if ar <= 0.10:
            fails.append("avg_r_not_above_0_10")
    except (TypeError, ValueError):
        fails.append("avg_r_missing_or_invalid")

    try:
        pf = float(_pick_metric(metrics, "profit_factor") if _pick_metric(metrics, "profit_factor") is not None else float("nan"))
        if pf <= 1.25:
            fails.append("profit_factor_not_above_1_25")
    except (TypeError, ValueError):
        fails.append("profit_factor_missing_or_invalid")

    try:
        mdd = float(_pick_metric(metrics, "max_drawdown_r") if _pick_metric(metrics, "max_drawdown_r") is not None else float("nan"))
        if mdd <= -8.0:
            fails.append("max_drawdown_r_not_better_than_negative_8r")
    except (TypeError, ValueError):
        fails.append("max_drawdown_r_missing_or_invalid")

    try:
        rv = int(_pick_metric(metrics, "rule_violations") if _pick_metric(metrics, "rule_violations") is not None else -1)
        if rv != 0:
            fails.append("rule_violations_not_zero")
    except (TypeError, ValueError):
        fails.append("rule_violations_missing_or_invalid")

    spa = _pick_metric(metrics, "spread_slippage_acceptable")
    if spa is not True:
        fails.append("spread_slippage_not_acceptable")

    saf = _pick_metric(metrics, "small_account_feasible")
    if saf is not True:
        fails.append("small_account_not_feasible")

    return len(fails) == 0, fails


def _model_thresholds_pass(metrics: dict[str, Any]) -> tuple[bool, list[str]]:
    ok, fails = _strategy_thresholds_pass(metrics)
    if not ok:
        pass  # keep failing reasons from shared promotion gate

    vs = _pick_metric(metrics, "validation_score")
    if vs is None:
        fails.append("validation_score_missing")
    else:
        try:
            float(vs)
        except (TypeError, ValueError):
            fails.append("validation_score_invalid")

    cs = _pick_metric(metrics, "calibration_status")
    if cs is None or str(cs).strip() == "":
        fails.append("calibration_status_missing")

    pe = _pick_metric(metrics, "prediction_error_r")
    if pe is None:
        fails.append("prediction_error_r_missing")
    else:
        try:
            float(pe)
        except (TypeError, ValueError):
            fails.append("prediction_error_r_invalid")

    return len(fails) == 0, sorted(set(fails))


def _latest_strategy_map(records: list[StrategyEvidenceOut]) -> dict[str, StrategyEvidenceOut]:
    best: dict[str, StrategyEvidenceOut] = {}
    for r in records:
        if (r.horizon or "").lower() != "day_trading":
            continue
        cur = best.get(r.strategy_key)
        if cur is None or (r.updated_at or "") > (cur.updated_at or ""):
            best[r.strategy_key] = r
    return best


def _latest_model_map(records: list[ModelEvidenceOut]) -> dict[str, ModelEvidenceOut]:
    best: dict[str, ModelEvidenceOut] = {}
    for r in records:
        if (r.horizon or "").lower() != "day_trading":
            continue
        cur = best.get(r.model_key)
        if cur is None or (r.updated_at or "") > (cur.updated_at or ""):
            best[r.model_key] = r
    return best


def _strategy_row(cfg: StrategyConfig, ev: StrategyEvidenceOut | None) -> StrategyPromotionRow:
    setup_type = cfg.timeframe or "unknown"
    metrics = dict(ev.metrics or {}) if ev else {}

    if ev is None:
        status = "backtest_required" if cfg.requires_backtest else "research_only"
        return StrategyPromotionRow(
            strategy_key=cfg.strategy_key,
            display_name=cfg.display_name,
            setup_type=setup_type,
            status=status,
            sample_size=None,
            avg_r=None,
            profit_factor=None,
            max_drawdown_r=None,
            rule_violations=None,
            spread_slippage_acceptable=None,
            small_account_feasible=None,
            promotion_readiness="not_ready",
            blockers=["missing_evidence"],
            next_action="Record strategy evidence for day_trading horizon with promotion metrics.",
        )

    base_blockers = list(ev.blockers or [])
    ok, fails = _strategy_thresholds_pass(metrics)
    readiness: Literal["not_ready", "eligible_for_review"] = "eligible_for_review" if ok else "not_ready"
    merged_blockers = sorted(set(base_blockers + (fails if not ok else [])))

    ext_status = (ev.status or "research_only").lower()
    if ext_status in {"blocked"}:
        readiness = "not_ready"

    next_action = (
        "Eligible for human promotion review (does not activate automatically)."
        if readiness == "eligible_for_review"
        else "Complete evidence metrics and resolve blockers before promotion review."
    )

    def _oint(key: str) -> int | None:
        v = _pick_metric(metrics, key)
        if v is None:
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    def _ofloat(key: str) -> float | None:
        v = _pick_metric(metrics, key)
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    def _obool(key: str) -> bool | None:
        v = _pick_metric(metrics, key)
        if v is None:
            return None
        if isinstance(v, bool):
            return v
        return None

    return StrategyPromotionRow(
        strategy_key=cfg.strategy_key,
        display_name=cfg.display_name,
        setup_type=setup_type,
        status=ev.status or "research_only",
        sample_size=_oint("sample_size"),
        avg_r=_ofloat("avg_r"),
        profit_factor=_ofloat("profit_factor"),
        max_drawdown_r=_ofloat("max_drawdown_r"),
        rule_violations=_oint("rule_violations"),
        spread_slippage_acceptable=_obool("spread_slippage_acceptable"),
        small_account_feasible=_obool("small_account_feasible"),
        promotion_readiness=readiness,
        blockers=merged_blockers,
        next_action=next_action,
    )


def _model_row(reg: dict[str, Any], ev: ModelEvidenceOut | None) -> ModelPromotionRow:
    model_key = str(reg.get("model_key") or "")
    model_role = str(reg.get("group") or "unknown")
    reg_status = str(reg.get("status") or "unknown")

    allowed_raw = _pick_metric(dict(ev.metrics or {}) if ev else {}, "allowed_strategy_keys")
    allowed_strategy_keys = list(allowed_raw) if isinstance(allowed_raw, list) else []

    if ev is None:
        return ModelPromotionRow(
            model_key=model_key,
            model_role=model_role,
            status="research_only",
            allowed_strategy_keys=allowed_strategy_keys,
            sample_size=None,
            validation_score=None,
            calibration_status=None,
            prediction_error_r=None,
            promotion_readiness="not_ready",
            blockers=["missing_evidence"],
            next_action="Record model evidence for day_trading horizon with promotion metrics.",
        )

    metrics = dict(ev.metrics or {})
    base_blockers = list(ev.blockers or [])
    ok, fails = _model_thresholds_pass(metrics)
    readiness: Literal["not_ready", "eligible_for_review"] = "eligible_for_review" if ok else "not_ready"
    merged = sorted(set(base_blockers + (fails if not ok else [])))
    if (ev.status or "").lower() == "blocked":
        readiness = "not_ready"

    def _oint(key: str) -> int | None:
        v = _pick_metric(metrics, key)
        if v is None:
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    def _ofloat(key: str) -> float | None:
        v = _pick_metric(metrics, key)
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    vs = _ofloat("validation_score")
    pe = _ofloat("prediction_error_r")
    cs = _pick_metric(metrics, "calibration_status")
    cs_out = str(cs) if cs is not None else None

    next_action = (
        "Eligible for human promotion review (does not activate automatically)."
        if readiness == "eligible_for_review"
        else "Complete model evidence metrics and resolve blockers before promotion review."
    )

    return ModelPromotionRow(
        model_key=model_key,
        model_role=model_role,
        status=ev.status or reg_status,
        allowed_strategy_keys=allowed_strategy_keys,
        sample_size=_oint("sample_size"),
        validation_score=vs,
        calibration_status=cs_out,
        prediction_error_r=pe,
        promotion_readiness=readiness,
        blockers=merged,
        next_action=next_action,
    )


def get_promotion_strategies_status() -> PromotionStrategiesResponse:
    evidence_list = list_strategy_evidence(limit=500)
    by_s = _latest_strategy_map(evidence_list)
    rows: list[StrategyPromotionRow] = []
    for cfg in list_strategies():
        if (cfg.timeframe or "").lower() != "day_trade":
            continue
        rows.append(_strategy_row(cfg, by_s.get(cfg.strategy_key)))
    rows.sort(key=lambda r: r.strategy_key)
    return PromotionStrategiesResponse(strategies=rows)


def get_promotion_models_status() -> PromotionModelsResponse:
    reg = get_model_registry()
    models = list(reg.get("models") or [])
    evidence_list = list_model_evidence(limit=500)
    by_m = _latest_model_map(evidence_list)
    rows = [_model_row(m, by_m.get(str(m.get("model_key") or ""))) for m in models]
    rows.sort(key=lambda r: r.model_key)
    return PromotionModelsResponse(models=rows)
