from datetime import datetime, timezone

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


@router.get("/data-quality/status", response_model=DataQualityStatusResponse)
def get_data_quality_status():
    """
    Pipeline-level data quality rollup for UI/status pages.

    v1 is intentionally conservative: it reports visibility only and does not
    claim symbols are continuously checked unless that pipeline exists.
    """
    now = datetime.now(timezone.utc).isoformat()
    return DataQualityStatusResponse(
        status="ok",
        data_mode="summary",
        updated_at=now,
        summary={
            "status": "partial",
            "checks_configured": 0,
            "symbols_checked_today": 0,
            "pass": 0,
            "warnings": 0,
            "fails": 0,
        },
        checks=[
            DataQualityCheckStatus(
                check="Market Snapshot Freshness",
                status="partial",
                description="Symbol-level freshness is validated when /api/data-quality/{symbol} runs.",
                input_stage="Market Data",
                blocks_downstream=True,
                downstream_consumers=["Feature Store", "Signals"],
                next_action="Run /api/data-quality/{symbol}?asset_class=stock&source=auto for a candidate symbol.",
                last_checked=None,
            )
        ],
    )


@router.get("/data-quality/{symbol}", response_model=DataQualityReport)
def get_data_quality(symbol: str, asset_class: str = Query("stock"), source: str = Query("auto")):
    return check_market_data_quality(symbol, asset_class=asset_class, source=source)
