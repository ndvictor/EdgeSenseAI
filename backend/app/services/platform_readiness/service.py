"""Service entrypoints for Phase 6 platform readiness reporting."""

from __future__ import annotations

from app.services.platform_readiness.final_report import build_final_readiness_status

__all__ = ["build_final_readiness_status", "build_final_readiness_payload"]


def build_final_readiness_payload() -> dict:
    """Alias for API responses (dict form)."""
    return build_final_readiness_status()
