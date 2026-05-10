from __future__ import annotations

import hashlib
from collections import Counter
from typing import Any

from app.services.alpha_engine.models import AlphaCandidateScore, AlphaEngineRequest, AlphaEntryPlan, AlphaRecommendation, CandidateFeatureRow
from app.services.alpha_engine.playbook_registry import get_intraday_playbooks
from app.services.alpha_engine.scoring import (
    clamp_score,
    compute_final_score,
    estimate_entry_plan,
    score_liquidity,
    score_relative_volume,
    score_small_account_fit,
    score_spread,
    score_trend,
)

ALLOWED_SOURCES = {"provider", "scanner", "persisted_watchlist", "feature_store"}

DEFAULT_PREDICTION_HORIZON_MINUTES = 60


def _clamp_heuristic_win_probability(p: float) -> float:
    return max(0.35, min(0.70, p))


def _deterministic_recommendation_id(
    symbol: str,
    strategy_key: str,
    final_score: float,
    entry: float | None,
    stop: float | None,
) -> str:
    raw = f"{symbol}|{strategy_key}|{final_score:.6f}|{entry}|{stop}"
    return "alpha_" + hashlib.sha256(raw.encode()).hexdigest()[:24]


def _trained_model_evidence_and_key(
    request: AlphaEngineRequest,
    symbol: str,
    strategy_key: str,
) -> tuple[bool, str | None]:
    meta = request.metadata or {}
    ev = meta.get("trained_model_evidence")
    mk = meta.get("prediction_model_key")
    has_evidence = False
    if isinstance(ev, dict):
        sym_u = symbol.upper()
        has_evidence = bool(ev.get(sym_u) or ev.get(symbol) or ev.get(strategy_key) or ev.get("global"))
    elif ev is True:
        has_evidence = True
    if has_evidence and isinstance(mk, str) and mk.strip():
        return True, mk.strip()
    return False, None


def _heuristic_win_probability(component_scores: dict[str, float], final_score: float | None) -> float:
    p = 0.50
    fs = float(final_score or 0.0)
    if fs >= 80:
        p += 0.10
    if component_scores.get("relative_volume_score", 0.0) >= 75:
        p += 0.05
    if component_scores.get("spread_score", 0.0) >= 80:
        p += 0.05
    if component_scores.get("evidence_score", 0.0) >= 60:
        p += 0.05
    return round(_clamp_heuristic_win_probability(p), 6)


def _prediction_attachment(
    *,
    request: AlphaEngineRequest,
    symbol: str,
    strategy_key: str,
    final_score: float | None,
    component_scores: dict[str, float],
    entry_plan: AlphaEntryPlan,
) -> dict[str, Any]:
    trained, trained_key = _trained_model_evidence_and_key(request, symbol, strategy_key)
    extra_warnings: list[str] = []
    if trained and trained_key:
        model_key = trained_key
        prediction_reason = (
            f"prediction_model_key={model_key} from request metadata (trained_model_evidence present); "
            "win probability and EV use the same deterministic Alpha score calibration as heuristic_alpha_v1 "
            "until dedicated inference is wired."
        )
    else:
        model_key = "heuristic_alpha_v1"
        extra_warnings.append("heuristic_prediction_not_trained_model")
        prediction_reason = (
            "Deterministic heuristic_alpha_v1: base win probability 0.50 with +0.10 if final_score>=80, "
            "+0.05 if relative_volume_score>=75, +0.05 if spread_score>=80, +0.05 if evidence_score>=60; "
            "clamped to [0.35, 0.70]. predicted_expected_value_r = p*target_r - (1-p)*1R using "
            "entry_plan.expected_r as target_r."
        )

    win_p = _heuristic_win_probability(component_scores, final_score)
    target_r = entry_plan.expected_r
    predicted_expected_value_r: float | None = None
    predicted_return_r: float | None = None
    predicted_return_pct: float | None = None

    if target_r is not None:
        tr = float(target_r)
        predicted_expected_value_r = round(win_p * tr - (1.0 - win_p) * 1.0, 6)
        predicted_return_r = predicted_expected_value_r

    entry = entry_plan.entry
    risk = entry_plan.risk_per_share
    if (
        predicted_return_r is not None
        and entry is not None
        and risk is not None
        and float(entry) != 0
        and float(risk) > 0
    ):
        predicted_return_pct = round(float(predicted_return_r) * float(risk) / float(entry) * 100.0, 6)
    elif predicted_return_r is not None:
        extra_warnings.append("prediction_pct_unavailable_missing_entry_or_risk")

    recommendation_id = _deterministic_recommendation_id(
        symbol,
        strategy_key,
        float(final_score or 0.0),
        entry,
        entry_plan.stop,
    )

    return {
        "recommendation_id": recommendation_id,
        "predicted_win_probability": win_p,
        "predicted_expected_value_r": predicted_expected_value_r,
        "predicted_return_r": predicted_return_r,
        "predicted_return_pct": predicted_return_pct,
        "prediction_horizon_minutes": DEFAULT_PREDICTION_HORIZON_MINUTES,
        "prediction_model_key": model_key,
        "prediction_reason": prediction_reason,
        "extra_warnings": extra_warnings,
    }


def _reject_reasons(row: CandidateFeatureRow) -> list[str]:
    reasons: list[str] = []
    if not row.symbol:
        reasons.append("symbol_missing")
    if row.synthetic:
        reasons.append("synthetic_candidate_rejected")
    if row.mock:
        reasons.append("mock_candidate_rejected")
    if row.source not in ALLOWED_SOURCES:
        reasons.append("unsupported_candidate_source")
    if row.last_price is None:
        reasons.append("last_price_missing")
    elif row.last_price < 2:
        reasons.append("price_below_minimum")
    if row.spread_bps is None:
        reasons.append("spread_bps_missing")
    elif row.spread_bps > 20:
        reasons.append("spread_too_wide")
    if row.volume is None:
        reasons.append("volume_missing")
    if row.avg_volume is None:
        reasons.append("avg_volume_missing")
    if row.relative_volume is None:
        reasons.append("relative_volume_missing")
    elif row.relative_volume < 1.2:
        reasons.append("relative_volume_too_low")
    return reasons


def _strategy_fit(row: CandidateFeatureRow, playbook: dict[str, Any]) -> tuple[float, list[str], list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []
    session = row.session_state
    allowed_sessions = set(playbook.get("allowed_sessions") or [])
    if session and allowed_sessions and session not in allowed_sessions:
        blockers.append("session_not_allowed_for_playbook")
    if row.last_price is not None:
        if row.last_price < float(playbook.get("min_price") or 0):
            blockers.append("price_below_playbook_minimum")
        if row.last_price > float(playbook.get("max_price") or 10**9):
            warnings.append("high_price_reduces_flexibility")
    if row.spread_bps is not None and row.spread_bps > float(playbook.get("max_spread_bps") or 20):
        blockers.append("spread_exceeds_playbook_limit")

    liquidity = score_liquidity(row)
    trend = score_trend(row)
    rv = float(row.relative_volume or 0)
    if rv < float(playbook.get("min_relative_volume") or 0):
        blockers.append("relative_volume_below_playbook_minimum")
    if liquidity < float(playbook.get("min_liquidity_score") or 0):
        blockers.append("liquidity_below_playbook_minimum")
    if trend < float(playbook.get("min_trend_score") or 0):
        blockers.append("trend_below_playbook_minimum")
    if playbook.get("requires_price_above_vwap") and row.price_above_vwap is not True:
        blockers.append("price_not_above_vwap")

    score = 50.0
    if row.price_above_vwap is True and playbook.get("requires_price_above_vwap"):
        score += 15.0
    if row.relative_volume and row.relative_volume >= float(playbook.get("min_relative_volume") or 0) * 1.5:
        score += 12.0
    if liquidity >= float(playbook.get("min_liquidity_score") or 0):
        score += 8.0
    if trend >= float(playbook.get("min_trend_score") or 0):
        score += 8.0
    if playbook.get("setup_type") == "opening_range_breakout" and row.opening_range_high is not None:
        score += 10.0
    if playbook.get("setup_type") == "liquidity_reclaim" and (row.vwap is not None or row.opening_range_low is not None):
        score += 10.0
    return clamp_score(score), blockers, warnings


def _score_candidate(row: CandidateFeatureRow, playbook: dict[str, Any], request: AlphaEngineRequest) -> AlphaCandidateScore:
    symbol = str(row.symbol or "").strip().upper()
    warnings: list[str] = []
    strategy_key = str(playbook["strategy_key"])
    strategy_fit_score, blockers, fit_warnings = _strategy_fit(row, playbook)
    warnings.extend(fit_warnings)

    evidence_present = strategy_key in request.evidence_score_by_strategy
    evidence_score = clamp_score(request.evidence_score_by_strategy.get(strategy_key), default=35.0)
    if not evidence_present:
        warnings.append("proof_missing_or_backtest_required")
    model_score = clamp_score(request.model_score_by_symbol.get(symbol), default=40.0)
    small_account_score, small_account_warnings = score_small_account_fit(row, request.account_equity, max_price=float(playbook.get("max_price") or 75))
    warnings.extend(small_account_warnings)

    component_scores = {
        "liquidity_score": score_liquidity(row),
        "relative_volume_score": score_relative_volume(row.relative_volume),
        "trend_score": score_trend(row),
        "strategy_fit_score": strategy_fit_score,
        "spread_score": score_spread(row.spread_bps, max_spread_bps=float(playbook.get("max_spread_bps") or 20)),
        "evidence_score": evidence_score,
        "model_score": model_score,
        "small_account_score": small_account_score,
    }
    final_score = compute_final_score(component_scores)
    if small_account_score <= 0:
        blockers.append("small_account_fit_failed")
    entry_plan = estimate_entry_plan(row, playbook, request.max_risk_dollars)
    if entry_plan.position_size_estimate is not None and entry_plan.position_size_estimate <= 0:
        warnings.append("position_size_estimate_zero_for_risk_limit")
    reason = f"{symbol} scored for {strategy_key} using real candidate features."
    return AlphaCandidateScore(
        symbol=symbol,
        strategy_key=strategy_key,
        setup_type=str(playbook.get("setup_type") or ""),
        final_score=final_score,
        confidence=clamp_score(final_score * 0.9),
        entry_plan=entry_plan,
        blockers=sorted(set(blockers)),
        warnings=sorted(set(warnings)),
        reason=reason,
        component_scores=component_scores,
    )


def _no_qualified(reason: str, blockers: list[str] | None = None, warnings: list[str] | None = None) -> AlphaRecommendation:
    return AlphaRecommendation(
        status="no_qualified_setup",
        symbol=None,
        reason=reason,
        blockers=sorted(set(blockers or [])),
        warnings=sorted(set(warnings or [])),
        mock_data_used=False,
        synthetic_data_used=False,
        submitted_order=False,
        broker_called=False,
        llm_used_for_trade_decision=False,
    )


def generate_alpha_recommendation(request: AlphaEngineRequest) -> AlphaRecommendation:
    if not request.candidates:
        return _no_qualified("No real scanner/provider candidates were supplied.")

    rejected: list[str] = []
    valid: list[CandidateFeatureRow] = []
    for row in request.candidates:
        reasons = _reject_reasons(row)
        if reasons:
            rejected.extend(reasons)
            continue
        valid.append(row)

    if not valid:
        counts = Counter(rejected)
        reason = "No candidate passed Alpha Engine validation: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
        status = "data_unavailable" if any("missing" in item for item in rejected) else "no_qualified_setup"
        return AlphaRecommendation(
            status=status,
            reason=reason,
            blockers=sorted(set(rejected)),
            mock_data_used=False,
            synthetic_data_used=False,
            submitted_order=False,
            broker_called=False,
            llm_used_for_trade_decision=False,
        )

    playbooks = [p for p in get_intraday_playbooks() if p.get("status") == "active" and p.get("setup_type") != "no_trade"]
    scored: list[AlphaCandidateScore] = []
    for row in valid:
        effective_row = row.model_copy(update={"session_state": row.session_state or request.session_state})
        for playbook in playbooks:
            candidate_score = _score_candidate(effective_row, playbook, request)
            if not candidate_score.blockers:
                scored.append(candidate_score)

    if not scored:
        return _no_qualified(
            "No valid candidate matched an active Alpha Engine playbook.",
            blockers=["no_active_playbook_match"],
            warnings=["proof_missing_or_backtest_required"] if not request.evidence_score_by_strategy else [],
        )

    best = sorted(scored, key=lambda item: (-item.final_score, item.symbol, item.strategy_key))[0]
    if best.final_score >= 80:
        status = "candidate_selected"
        warnings = list(best.warnings)
    elif best.final_score >= 65:
        status = "watchlist_only"
        warnings = sorted(set(best.warnings + ["candidate_needs_confirmation"]))
    else:
        return _no_qualified("Best Alpha Engine candidate scored below qualification threshold.", blockers=["alpha_score_below_threshold"], warnings=best.warnings)

    reason = (
        f"Selected {best.strategy_key} because {best.symbol} has qualifying real candidate features, "
        "controlled spread, acceptable liquidity, and small-account fit."
    )
    pred = _prediction_attachment(
        request=request,
        symbol=best.symbol,
        strategy_key=best.strategy_key,
        final_score=best.final_score,
        component_scores=best.component_scores,
        entry_plan=best.entry_plan,
    )
    pred_warnings = pred.pop("extra_warnings")
    warnings = sorted(set(warnings + pred_warnings))
    return AlphaRecommendation(
        status=status,
        symbol=best.symbol,
        strategy_key=best.strategy_key,
        setup_type=best.setup_type,
        scanner_score=best.component_scores.get("relative_volume_score"),
        model_score=best.component_scores.get("model_score"),
        evidence_score=best.component_scores.get("evidence_score"),
        small_account_score=best.component_scores.get("small_account_score"),
        strategy_fit_score=best.component_scores.get("strategy_fit_score"),
        final_score=best.final_score,
        confidence=best.confidence,
        entry_plan=best.entry_plan,
        evidence_summary={
            "evidence_score": best.component_scores.get("evidence_score"),
            "proof_status": request.proof_status_by_strategy.get(best.strategy_key, "not_proven"),
        },
        risk_summary={
            "account_equity": request.account_equity,
            "max_risk_dollars": request.max_risk_dollars,
            "max_daily_loss_dollars": request.max_daily_loss_dollars,
            "small_account_score": best.component_scores.get("small_account_score"),
            "position_size_estimate": best.entry_plan.position_size_estimate,
        },
        warnings=warnings,
        reason=reason,
        mock_data_used=False,
        synthetic_data_used=False,
        submitted_order=False,
        broker_called=False,
        llm_used_for_trade_decision=False,
        recommendation_id=pred["recommendation_id"],
        predicted_return_pct=pred["predicted_return_pct"],
        predicted_return_r=pred["predicted_return_r"],
        predicted_win_probability=pred["predicted_win_probability"],
        predicted_expected_value_r=pred["predicted_expected_value_r"],
        prediction_horizon_minutes=pred["prediction_horizon_minutes"],
        prediction_model_key=pred["prediction_model_key"],
        prediction_reason=pred["prediction_reason"],
    )
