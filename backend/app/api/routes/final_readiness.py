"""Phase 6 final platform completion readiness (no broker, no LLM, deterministic)."""

from __future__ import annotations

from fastapi import APIRouter

from app.services.platform_readiness.final_report import build_final_readiness_status

router = APIRouter(prefix="/final-readiness", tags=["final-readiness"])


@router.get("/status")
def get_final_readiness():
    return build_final_readiness_status()
