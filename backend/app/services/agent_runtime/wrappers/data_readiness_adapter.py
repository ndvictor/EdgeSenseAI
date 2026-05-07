from __future__ import annotations

from typing import Any

from app.services.feature_store_service import FeatureStoreRunRequest, run_feature_store_pipeline


def evaluate_data_readiness(*, symbols: list[str], asset_class: str, horizon: str, source: str = "auto") -> dict[str, Any]:
    """Best-effort deterministic data readiness check.

    Uses existing feature-store pipeline (which itself is source-backed or mock-backed).
    Never triggers execution/broker calls; safe for v1.
    """
    blockers: list[str] = []
    warnings: list[str] = []
    provider_status: dict[str, Any] = {}

    if not symbols:
        return {
            "decision": "blocked",
            "blockers": ["no_symbols_selected"],
            "warnings": [],
            "artifacts": {"provider_status": {}, "freshness_status": "unknown", "quality_status": "unknown", "source_mode": "placeholder"},
            "next_action": "Provide at least one symbol.",
        }

    rows = []
    for sym in symbols[:5]:
        resp = run_feature_store_pipeline(FeatureStoreRunRequest(symbol=sym, asset_class=asset_class, horizon=horizon, source=source))
        rows.append(resp.row)
        warnings.extend(resp.warnings or [])
        provider_status[sym.upper()] = {
            "provider": resp.normalized_snapshot.provider,
            "is_mock": bool(resp.normalized_snapshot.is_mock),
            "quality_status": resp.quality_report.quality_status,
            "blockers": resp.quality_report.blockers or [],
        }
        if resp.quality_report.quality_status == "fail":
            blockers.extend(resp.quality_report.blockers or ["data_quality_fail"])

    quality_status = "pass" if not blockers else "fail"
    source_mode = "source_backed" if any(not v.get("is_mock") for v in provider_status.values()) else "placeholder"
    decision = "data_ready" if quality_status == "pass" else "blocked"
    return {
        "decision": decision,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "artifacts": {
            "provider_status": provider_status,
            "freshness_status": "best_effort",
            "quality_status": quality_status,
            "source_mode": source_mode,
        },
        "next_action": "Proceed to market condition scan." if decision != "blocked" else "Resolve data quality blockers or allow mock data in upstream systems.",
    }

