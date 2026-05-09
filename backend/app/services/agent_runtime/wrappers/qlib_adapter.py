from __future__ import annotations

from typing import Any

from app.services.qlib_integration.service import get_latest_signal_scores, get_qlib_status, list_artifacts


def _with_applicability(artifact: Any, *, horizon: str) -> dict[str, Any]:
    data = artifact.model_dump()
    data["applicable_to_current_workflow"] = data.get("horizon") == horizon == "day_trading"
    if not data["applicable_to_current_workflow"]:
        data["warnings"] = sorted(set(list(data.get("warnings") or []) + ["Research only — not active in autonomous workflow"]))
    return data


def qlib_research_snapshot(*, limit: int = 10, horizon: str = "day_trading") -> dict[str, Any]:
    status = get_qlib_status()
    latest_scores = get_latest_signal_scores()
    latest_artifacts = list_artifacts(limit=limit)
    backtests = [a for a in latest_artifacts if a.artifact_type == "backtest"]
    models = [a for a in latest_artifacts if a.artifact_type == "model"]
    applicable_backtests = [a for a in backtests if a.horizon == "day_trading"]
    applicable_models = [a for a in models if a.horizon == "day_trading"]
    return {
        "qlib_available": bool(status.qlib_available),
        "qlib_version": status.qlib_version,
        "configured": bool(status.configured),
        "artifact_count": status.artifact_count,
        "latest_signal_count": status.latest_signal_count,
        "latest_backtest_count": status.latest_backtest_count,
        "latest_model_count": status.latest_model_count,
        "qlib_artifact_counts": {
            "signal": status.latest_signal_count,
            "backtest": status.latest_backtest_count,
            "model": status.latest_model_count,
            "total": status.artifact_count,
        },
        "qlib_artifact_id": (latest_scores.artifact_id if latest_scores and latest_scores.horizon == "day_trading" else None)
        or (applicable_backtests[0].artifact_id if applicable_backtests else None)
        or (applicable_models[0].artifact_id if applicable_models else None),
        "supported_tasks": ["signal_scoring_record", "artifact_registry_record"],
        "latest_signal_scores": _with_applicability(latest_scores, horizon=horizon) if latest_scores else None,
        "latest_backtest_artifacts": [_with_applicability(a, horizon=horizon) for a in backtests][:5],
        "latest_model_artifacts": [_with_applicability(a, horizon=horizon) for a in models][:5],
        "qlib_status_blockers": status.blockers,
        "blockers": [],
        "warnings": sorted(set(list(status.warnings or []) + list(status.blockers or []))),
        "next_agent": "model_selection_agent" if models or latest_scores else "backtest_validation_agent",
        "next_action": status.next_action,
    }

