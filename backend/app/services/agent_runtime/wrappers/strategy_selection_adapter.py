from __future__ import annotations

from typing import Any

from app.services.strategy_ranking_service import StrategyRankingRequest, run_strategy_ranking
from app.services.strategy_evidence.models import StrategyEvidenceCreate
from app.services.strategy_evidence.service import save_strategy_evidence


def select_strategy(*, market_phase: str, active_loop: str, regime: str, horizon: str) -> dict[str, Any]:
    """Use existing strategy ranking service and persist a strategy evidence record."""
    req = StrategyRankingRequest(
        market_phase=market_phase,
        active_loop=active_loop,
        regime=regime,
        horizon=horizon,
        account_equity=10000,
        buying_power=10000,
        strategy_keys=None,
        source="phase_3_glue_agent",
        research_mode=False,
    )
    resp = run_strategy_ranking(req)
    ranked = [r.model_dump() for r in resp.ranked_strategies]
    top = resp.top_strategy_key

    if top:
        top_item = next((r for r in resp.ranked_strategies if r.strategy_key == top), None)
        save_strategy_evidence(
            StrategyEvidenceCreate(
                strategy_key=top,
                strategy_group=str(getattr(top_item, "strategy_family", "unknown")) if top_item else "unknown",
                asset_class="stock",
                horizon="day_trading" if horizon in {"day_trade", "day_trading"} else horizon,
                status="selected",
                strategy_score=float(getattr(top_item, "strategy_score", 0.0)) if top_item else None,
                proof_status=None,
                selected_model_keys=list(getattr(top_item, "model_stack_hint", []) or []) if top_item else [],
                scanner_needs=list(getattr(top_item, "scanner_needs", []) or []) if top_item else [],
                data_needs=list(getattr(top_item, "data_needs", []) or []) if top_item else [],
                metrics={"ranking_run_id": resp.run_id},
                blockers=list(getattr(top_item, "blockers", []) or []) if top_item else [],
                warnings=list(getattr(top_item, "warnings", []) or []) if top_item else [],
            )
        )

    return {
        "selected_strategy_key": top,
        "ranked_strategies": ranked,
        "active_strategies": resp.active_strategies,
        "research_candidates": resp.recommended_research_candidate_keys,
        "strategy_score": next((r.strategy_score for r in resp.ranked_strategies if r.strategy_key == top), None) if top else None,
        "next_action": "Proceed to model selection." if top else "No strategy selected; review ranking blockers.",
    }

