from __future__ import annotations

from typing import Any

from app.services.proof_registry.service import evaluate_proof_status, list_proof_records
from app.services.qlib_integration.service import list_artifacts


def validate_backtest_or_proof(*, strategy_key: str, asset_class: str, horizon: str) -> dict[str, Any]:
    """Use proof_registry_records as source of truth when available; never fake proof."""
    if (horizon or "").strip().lower() != "day_trading":
        return {
            "proof_status": "research_only",
            "backtest_status": "not_applicable",
            "paper_status": "not_applicable",
            "sample_size": 0,
            "avg_r_multiple": 0.0,
            "max_drawdown_r": None,
            "blockers": ["horizon_not_supported_for_autonomous_workflow"],
            "warnings": ["proof_horizon_not_applicable_to_autonomous_workflow"],
            "supported_horizons": ["day_trading"],
            "next_action": "Autonomous workflow is day-trading only.",
        }
    records = list_proof_records(limit=50)
    match = next((r for r in records if r.strategy_key == strategy_key and r.asset_class == asset_class and r.horizon == horizon), None)
    if match is None:
        qlib_backtest = next(
            (
                a
                for a in list_artifacts(limit=50)
                if a.artifact_type == "backtest"
                and a.strategy_key == strategy_key
                and a.asset_class == asset_class
                and a.horizon == horizon
                and a.artifact_status in {"ready", "recorded"}
            ),
            None,
        )
        if qlib_backtest is not None:
            decision = evaluate_proof_status({**qlib_backtest.metrics, "strategy_key": strategy_key})
            return {
                **decision,
                "proof_id": None,
                "qlib_artifact_id": qlib_backtest.artifact_id,
                "backtest_status": "recorded",
                "paper_status": "unknown",
                "warnings": sorted(set(list(decision.get("warnings") or []) + ["proof_registry_record_missing_for_qlib_artifact"])),
            }
        return {
            "proof_status": "backtest_required" if strategy_key else "proof_required",
            "backtest_status": "unknown",
            "paper_status": "unknown",
            "sample_size": 0,
            "avg_r_multiple": 0.0,
            "max_drawdown_r": None,
            "blockers": ["no_proof_record_found"],
            "warnings": ["Proof is required; no record exists in proof registry."],
            "next_action": "Run backtest/paper validation and record proof into proof registry.",
        }

    decision = evaluate_proof_status(match)
    return {
        "proof_id": match.proof_id,
        "proof_status": decision["proof_status"],
        "backtest_status": "recorded" if match.backtest_run_id else "unknown",
        "paper_status": "recorded" if match.paper_run_id else "unknown",
        "sample_size": match.sample_size,
        "avg_r_multiple": match.avg_r_multiple,
        "max_drawdown_r": match.max_drawdown_r,
        "blockers": decision.get("blockers", []),
        "warnings": decision.get("warnings", []),
        "next_action": decision.get("next_action", "Proof not sufficient; continue research/paper."),
    }

