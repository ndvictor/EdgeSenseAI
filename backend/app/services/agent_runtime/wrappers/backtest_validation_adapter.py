from __future__ import annotations

from typing import Any

from app.services.proof_registry.service import list_proof_records


def validate_backtest_or_proof(*, strategy_key: str, asset_class: str, horizon: str) -> dict[str, Any]:
    """Use proof_registry_records as source of truth when available; never fake proof."""
    records = list_proof_records(limit=50)
    match = next((r for r in records if r.strategy_key == strategy_key and r.asset_class == asset_class and r.horizon == horizon), None)
    if match is None:
        return {
            "proof_status": "proof_required",
            "backtest_status": "unknown",
            "paper_status": "unknown",
            "sample_size": 0,
            "avg_r_multiple": 0.0,
            "max_drawdown_r": None,
            "blockers": ["no_proof_record_found"],
            "warnings": ["Proof is required; no record exists in proof registry."],
            "next_action": "Run backtest/paper validation and record proof into proof registry.",
        }

    return {
        "proof_status": match.proof_status,
        "backtest_status": "recorded" if match.backtest_run_id else "unknown",
        "paper_status": "recorded" if match.paper_run_id else "unknown",
        "sample_size": match.sample_size,
        "avg_r_multiple": match.avg_r_multiple,
        "max_drawdown_r": match.max_drawdown_r,
        "blockers": match.blockers,
        "warnings": match.warnings,
        "next_action": "Proceed to strategy eligibility checks." if match.proof_status in {"proven", "paper_passed"} else "Proof not sufficient; continue research/paper.",
    }

