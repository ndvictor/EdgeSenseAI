"""Read-only promotion readiness endpoints. No activation or POST actions."""

from __future__ import annotations

from fastapi import APIRouter

from app.services.promotion_center.service import get_promotion_models_status, get_promotion_strategies_status

router = APIRouter(prefix="/promotion", tags=["promotion-center"])


@router.get("/strategies/status")
def promotion_strategies_status():
    return get_promotion_strategies_status().model_dump()


@router.get("/models/status")
def promotion_models_status():
    return get_promotion_models_status().model_dump()
