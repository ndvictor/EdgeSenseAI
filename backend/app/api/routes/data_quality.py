from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.services.data_quality_service import DataQualityReport, check_market_data_quality
router = APIRouter()


class DataQualityCheckStatus(BaseModel):
    check: str
    status: str
    description: str | None = None
    input_stage: str | None = None
    blocks_downstream: bool | None = None
    downstream_consumers: list[str] | None = None
    pass_count: int | None = None
    warn_count: int | None = None
    fail_count: int | None = None
    last_checked: str | None = None
    next_action: str | None = None


class DataQualityStatusResponse(BaseModel):
    status: str
    data_mode: str | None = None
    updated_at: str | None = None
    summary: dict | None = None
    checks: list[DataQualityCheckStatus] | None = None
    symbol_samples: list[dict] | None = None


@router.get("/data-quality/status", response_model=DataQualityStatusResponse)
def get_data_quality_status():
    """
    Pipeline-level data quality rollup for UI/status pages.

    v2 samples active candidate symbols (from the watchlist/candidate universe)
    and aggregates pass/warn/fail + stale/fresh + blockers (read-only).
    """
    from datetime import datetime, timezone

    from app.services.candidate_universe_service import CandidateStatus, list_candidates
    from app.services.market_data_service import MarketDataService

    now = datetime.now(timezone.utc).isoformat()
    market_data = MarketDataService()
    candidates = list_candidates(status=CandidateStatus.ACTIVE)
    candidates = sorted(candidates, key=lambda c: (-float(c.priority_score or 0), str(c.symbol)))
    sample = candidates[:20]

    pass_n = warn_n = fail_n = 0
    fresh_n = stale_n = unknown_n = 0
    pipeline_blockers: list[str] = []
    symbol_samples: list[dict] = []

    for c in sample:
        sym = (c.symbol or "").upper()
        try:
            snap = market_data.get_market_snapshot(sym, source="auto")
        except Exception as exc:  # noqa: BLE001
            fail_n += 1
            unknown_n += 1
            symbol_samples.append({"symbol": sym, "quality_status": "fail", "freshness_status": "unknown", "error": str(exc)[:240]})
            continue

        rep = check_market_data_quality(sym, asset_class=c.asset_class or "stock", source="auto", snapshot=snap)
        if rep.quality_status == "pass":
            pass_n += 1
        elif rep.quality_status == "warn":
            warn_n += 1
        else:
            fail_n += 1

        if rep.freshness_status == "fresh":
            fresh_n += 1
        elif rep.freshness_status == "stale":
            stale_n += 1
        else:
            unknown_n += 1

        pipeline_blockers.extend(rep.blockers)
        symbol_samples.append(
            {
                "symbol": rep.ticker,
                "quality_status": rep.quality_status,
                "freshness_status": rep.freshness_status,
                "data_source": rep.data_source,
                "provider": rep.provider,
                "blocker_count": len(rep.blockers),
                "warning_count": len(rep.warnings),
                "checked_at": rep.checked_at.isoformat(),
                "drilldown": f"/api/data-quality/{rep.ticker}?asset_class={c.asset_class or 'stock'}&source=auto",
            }
        )

    # rollup status
    if not candidates:
        rollup = "partial"
    elif fail_n > 0:
        rollup = "fail"
    elif warn_n > 0 or stale_n > 0:
        rollup = "warn"
    else:
        rollup = "pass" if sample else "partial"

    # stable-ish dedup
    dedup_blockers = list(dict.fromkeys(pipeline_blockers))[:30]

    check_status = "pass" if rollup == "pass" else ("fail" if rollup == "fail" else "partial")

    return DataQualityStatusResponse(
        status="ok",
        data_mode="candidate_rollup_v2",
        updated_at=now,
        summary={
            "status": rollup,
            "rollup_status": rollup,
            "active_candidates_in_universe": len(candidates),
            "symbols_sampled": len(sample),
            "symbols_checked_today": len(sample),
            "pass": pass_n,
            "warnings": warn_n,
            "fails": fail_n,
            "fresh": fresh_n,
            "stale": stale_n,
            "unknown_freshness": unknown_n,
            "checks_configured": 1,
            "pipeline_blockers": dedup_blockers,
        },
        checks=[
            DataQualityCheckStatus(
                check="Candidate universe market snapshot quality",
                status=check_status,
                description=(
                    f"Sampled {len(sample)} active candidate symbol(s): pass={pass_n}, warn={warn_n}, fail={fail_n}; "
                    f"fresh={fresh_n}, stale={stale_n}, unknown={unknown_n}."
                ),
                input_stage="Data Intake & Quality",
                blocks_downstream=True,
                downstream_consumers=["Feature Store", "Signals", "Execution Planner"],
                pass_count=pass_n,
                warn_count=warn_n,
                fail_count=fail_n,
                last_checked=now,
                next_action="Inspect failing symbols via /api/data-quality/{symbol} and resolve provider/freshness blockers.",
            )
        ],
        symbol_samples=symbol_samples,
    )


@router.get("/data-quality/{symbol}", response_model=DataQualityReport)
def get_data_quality(symbol: str, asset_class: str = Query("stock"), source: str = Query("auto")):
    return check_market_data_quality(symbol, asset_class=asset_class, source=source)
