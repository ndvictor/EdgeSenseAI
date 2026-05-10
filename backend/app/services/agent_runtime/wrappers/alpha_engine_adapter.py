from __future__ import annotations

from typing import Any

from app.services.alpha_engine import AlphaEngineRequest, CandidateFeatureRow, generate_alpha_recommendation


_ALLOWED_SOURCES = {"provider", "scanner", "persisted_watchlist", "feature_store"}


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bool_or_none(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _feature_row_to_candidate(row: dict[str, Any]) -> CandidateFeatureRow | None:
    symbol = row.get("symbol") or row.get("ticker")
    if not symbol:
        return None
    source = str(row.get("source") or row.get("source_mode") or "feature_store")
    if source == "runtime":
        source = "feature_store"
    return CandidateFeatureRow(
        symbol=str(symbol).strip().upper(),
        last_price=_float_or_none(row.get("last_price") or row.get("price") or row.get("close")),
        volume=_float_or_none(row.get("volume")),
        avg_volume=_float_or_none(row.get("avg_volume") or row.get("average_volume")),
        relative_volume=_float_or_none(row.get("relative_volume")),
        day_change_pct=_float_or_none(row.get("day_change_pct") or row.get("change_percent")),
        spread_bps=_float_or_none(row.get("spread_bps")),
        vwap=_float_or_none(row.get("vwap")),
        price_above_vwap=_bool_or_none(row.get("price_above_vwap")),
        opening_range_high=_float_or_none(row.get("opening_range_high")),
        opening_range_low=_float_or_none(row.get("opening_range_low")),
        premarket_high=_float_or_none(row.get("premarket_high")),
        premarket_low=_float_or_none(row.get("premarket_low")),
        high_of_day=_float_or_none(row.get("high_of_day") or row.get("day_high")),
        low_of_day=_float_or_none(row.get("low_of_day") or row.get("day_low")),
        trend_score=_float_or_none(row.get("trend_score")),
        liquidity_score=_float_or_none(row.get("liquidity_score")),
        volatility_score=_float_or_none(row.get("volatility_score")),
        session_state=row.get("session_state"),
        source=source if source in _ALLOWED_SOURCES else "feature_store",
        synthetic=bool(row.get("synthetic") or row.get("synthetic_data_used") or row.get("spread_synthetic")),
        non_real=bool(row.get("non_real") or row.get("is_non_real") or row.get("using_non_real_data")),
        provider_name=row.get("provider_name") or row.get("provider"),
        metadata={k: v for k, v in row.items() if k not in {"symbol", "ticker"}},
    )


def _candidate_from_symbol(symbol: str, *, source: str) -> CandidateFeatureRow:
    # This intentionally does not invent price/spread/volume. Alpha Engine will
    # reject incomplete rows rather than fabricate a recommendation.
    return CandidateFeatureRow(symbol=symbol.strip().upper(), source=source)


def _collect_candidate_rows(inputs: dict[str, Any]) -> list[CandidateFeatureRow]:
    out: list[CandidateFeatureRow] = []
    seen: set[tuple[str, str]] = set()

    for key in ("feature_rows", "scanner_candidates", "watchlist"):
        values = inputs.get(key)
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, dict):
                candidate = _feature_row_to_candidate(value)
            elif isinstance(value, str):
                source = "scanner" if key == "scanner_candidates" else "persisted_watchlist"
                candidate = _candidate_from_symbol(value, source=source)
            else:
                candidate = None
            if candidate is None or not candidate.symbol:
                continue
            marker = (candidate.symbol, candidate.source)
            if marker not in seen:
                seen.add(marker)
                out.append(candidate)

    usable_symbols = inputs.get("usable_symbols") if isinstance(inputs.get("usable_symbols"), list) else []
    for symbol in usable_symbols:
        if not symbol:
            continue
        candidate = _candidate_from_symbol(str(symbol), source="scanner")
        marker = (candidate.symbol or "", candidate.source)
        if marker not in seen:
            seen.add(marker)
            out.append(candidate)

    selected = inputs.get("selected_symbol") or inputs.get("symbol")
    if selected:
        candidate = _candidate_from_symbol(str(selected), source="persisted_watchlist")
        marker = (candidate.symbol or "", candidate.source)
        if marker not in seen:
            seen.add(marker)
            out.append(candidate)
    return out


def run_alpha_engine_selection(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    candidates = _collect_candidate_rows(inputs)
    request = AlphaEngineRequest(
        candidates=candidates,
        account_equity=float(inputs.get("account_equity") or 1000.0),
        max_risk_dollars=float(inputs.get("max_risk_dollars") or 5.0),
        max_daily_loss_dollars=float(inputs.get("max_daily_loss_dollars") or 15.0),
        session_state=inputs.get("session_state"),
        market_regime=inputs.get("regime"),
        model_score_by_symbol=inputs.get("model_score_by_symbol") if isinstance(inputs.get("model_score_by_symbol"), dict) else {},
        evidence_score_by_strategy=inputs.get("evidence_score_by_strategy") if isinstance(inputs.get("evidence_score_by_strategy"), dict) else {},
        proof_status_by_strategy=inputs.get("proof_status_by_strategy") if isinstance(inputs.get("proof_status_by_strategy"), dict) else {},
        metadata={"workflow_run_id": context.get("workflow_run_id"), "candidate_count": len(candidates)},
    )
    recommendation = generate_alpha_recommendation(request)
    payload = recommendation.model_dump()
    return {
        "alpha_recommendation": payload,
        "recommendation": payload,
        "alpha_status": recommendation.status,
        "alpha_selected_symbol": recommendation.symbol,
        "alpha_strategy_key": recommendation.strategy_key,
        "alpha_score": recommendation.final_score,
        "alpha_reason": recommendation.reason,
        "alpha_blockers": list(recommendation.blockers),
        "alpha_warnings": list(recommendation.warnings),
        "submitted_order": False,
        "broker_called": False,
        "llm_used": False,
        "next_action": "Proceed with Alpha-selected candidate." if recommendation.status == "candidate_selected" else "No Alpha Engine candidate selected.",
    }
