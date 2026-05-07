from __future__ import annotations

from typing import Any

from app.services.qlib_integration.service import get_latest_signal_scores, get_qlib_status, list_artifacts


def qlib_research_snapshot(*, limit: int = 10) -> dict[str, Any]:
    status = get_qlib_status()
    latest_scores = get_latest_signal_scores()
    latest_artifacts = list_artifacts(limit=limit)
    return {
        "qlib_available": bool(status.qlib_available),
        "qlib_version": status.qlib_version,
        "supported_tasks": ["signal_scoring_record", "artifact_registry_record"],
        "latest_signal_scores": latest_scores.model_dump() if latest_scores else None,
        "latest_backtest_artifacts": [a.model_dump() for a in latest_artifacts if a.artifact_type == "backtest"][:5],
        "latest_model_artifacts": [a.model_dump() for a in latest_artifacts if a.artifact_type == "model_artifact"][:5],
        "blockers": status.blockers,
        "warnings": status.warnings,
    }

