from __future__ import annotations

from typing import Any

from app.services.data_ingestion_service import build_data_ingestion_status
from app.services.data_quality_service import check_market_data_quality
from app.services.feature_store_service import FeatureStoreRunRequest, run_feature_store_pipeline
from app.services.market_data_service import MarketDataService
from app.services.normalization_status_service import build_normalization_status
from app.services.universe_selection_service import UniverseSelectionRequest, run_universe_selection
from app.services.workflow_orchestrator.models import OrchestratorRunRequest
from app.services.workflow_orchestrator.service import run_workflow

from app.services.pipeline_automation.models import (
    PipelineAutomationRunRequest,
    PipelineAutomationRunResponse,
    iso_utc_now,
    new_pipeline_run_id,
)

_LATEST: PipelineAutomationRunResponse | None = None


def get_latest_pipeline_run() -> PipelineAutomationRunResponse | None:
    return _LATEST


def run_pipeline(body: PipelineAutomationRunRequest) -> PipelineAutomationRunResponse:
    """Automate the 'feed → ingestion → quality → feature store → universe → orchestrator' chain.

    Notes:
    - "Data Feed" is represented by provider snapshots from MarketDataService.
    - "Ingestion" is currently a readiness summary; actual scheduled ingestion jobs can be wired later.
    - Universe builder uses Universe Selection (rank + freshness) and then hands the selected symbols to the orchestrator.
    """

    global _LATEST

    created_at = iso_utc_now()
    pipeline_run_id = new_pipeline_run_id()

    artifacts: dict[str, Any] = {
        "data_ingestion_status": build_data_ingestion_status().model_dump(),
        "normalization_status": build_normalization_status().model_dump(),
        "seed_symbols": list(body.seed_symbols),
    }

    # Step 1: pull feed snapshots + data quality for seed symbols (best-effort)
    src = body.source or "auto"
    market = MarketDataService()
    seed_symbols: list[str] = []
    warnings: list[str] = []
    blockers: list[str] = []
    for s in body.seed_symbols:
        sym = str(s).strip().upper()
        if sym and sym not in seed_symbols:
            seed_symbols.append(sym)
    if not seed_symbols:
        warnings.append("no_seed_symbols_provided")

    feed_samples: list[dict[str, Any]] = []
    quality_samples: list[dict[str, Any]] = []

    for sym in seed_symbols[: max(3, min(25, body.max_candidates * 3))]:
        snap = market.get_market_snapshot(sym, source=src)
        feed_samples.append(
            {
                "symbol": sym,
                "provider": snap.get("provider"),
                "data_quality": snap.get("data_quality"),
                "is_non_real": bool(snap.get("is_non_real")),
                "unavailable_fields": snap.get("unavailable_fields", []),
                "error": snap.get("error"),
            }
        )
        rep = check_market_data_quality(sym, asset_class=body.asset_class, source=src, snapshot=snap)
        quality_samples.append(rep.model_dump(mode="json"))
        warnings.extend(rep.warnings or [])

    artifacts["data_feed_samples"] = feed_samples
    artifacts["data_quality_seed_samples"] = quality_samples

    # Step 2: generate feature rows for a small subset (this is the "Feature Store" stage in v1)
    feature_runs: list[dict[str, Any]] = []
    feature_ok_symbols: list[str] = []
    for sym in seed_symbols[: min(10, max(3, body.max_candidates))]:
        fr = run_feature_store_pipeline(FeatureStoreRunRequest(symbol=sym, asset_class=body.asset_class, horizon=body.horizon, source=src))
        feature_runs.append(
            {
                "symbol": sym,
                "quality_status": fr.quality_report.quality_status,
                "data_source": fr.row.data_source,
                "provider": fr.quality_report.provider,
                "warnings": fr.warnings,
                "row_id": fr.row.id,
            }
        )
        if fr.quality_report.quality_status != "fail":
            feature_ok_symbols.append(sym)
    artifacts["feature_store_runs"] = feature_runs

    # Step 3: Universe builder / starter picker
    universe_req = UniverseSelectionRequest(
        symbols=(feature_ok_symbols or seed_symbols)[: max(5, body.max_candidates * 5)],
        asset_class=body.asset_class,  # type: ignore[arg-type]
        horizon=("day_trade" if body.horizon in ("day_trading", "day_trade") else body.horizon),  # type: ignore[arg-type]
        source=src,  # type: ignore[arg-type]
        max_candidates=max(1, min(100, int(body.max_candidates))),
        min_score=40,
    )
    universe = run_universe_selection(universe_req)
    artifacts["universe_selection"] = universe.model_dump(mode="json")

    selected_symbols = [str(c.symbol).upper() for c in (universe.selected_watchlist or []) if getattr(c, "symbol", None)]
    if not selected_symbols and universe.ranked_candidates:
        selected_symbols = [str(c.symbol).upper() for c in universe.ranked_candidates[: body.max_candidates] if getattr(c, "symbol", None)]
    selected_symbols = [s for i, s in enumerate(selected_symbols) if s and s not in selected_symbols[:i]]

    if not selected_symbols:
        blockers.extend(universe.blockers or ["no_symbols_selected_by_universe"])
        resp = PipelineAutomationRunResponse(
            pipeline_run_id=pipeline_run_id,
            status="blocked",
            orchestrator_run_id=None,
            workflow_run_id=None,
            selected_symbols=[],
            blockers=blockers,
            warnings=sorted(set(warnings)),
            artifacts=artifacts,
            next_action="Fix data feed/quality blockers, then re-run pipeline (universe selection returned no symbols).",
            created_at=created_at,
            updated_at=iso_utc_now(),
        )
        _LATEST = resp
        return resp

    # Step 4+: Hand off to existing workflow orchestrator (which runs the downstream agent pipeline)
    orch = run_workflow(
        OrchestratorRunRequest(
            asset_class=body.asset_class,
            horizon=body.horizon,
            mode=body.mode,
            source="pipeline_automation",
            symbols=selected_symbols,
            max_candidates=body.max_candidates,
            stop_at_stage=body.stop_at_stage,
            dry_run=body.dry_run,
            require_human_approval=body.require_human_approval,
            allow_submit=False,
            metadata={
                **(body.metadata or {}),
                "pipeline_run_id": pipeline_run_id,
                "pipeline_artifacts": {
                    "universe_run_id": getattr(universe, "run_id", None),
                    "feed_sample_count": len(feed_samples),
                    "feature_store_runs": feature_runs,
                },
            },
        )
    )

    resp = PipelineAutomationRunResponse(
        pipeline_run_id=pipeline_run_id,
        status=orch.status,
        orchestrator_run_id=orch.orchestrator_run_id,
        workflow_run_id=orch.workflow_run_id,
        selected_symbols=selected_symbols,
        blockers=list(orch.blockers or []),
        warnings=sorted(set(warnings + list(orch.warnings or []))),
        artifacts=artifacts,
        next_action=orch.next_action,
        created_at=created_at,
        updated_at=iso_utc_now(),
    )
    _LATEST = resp
    return resp

