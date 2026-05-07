"""Lab Platform — desired inventory registry (read-only, deterministic)."""

from fastapi import APIRouter

from app.services.lab_inventory_service import build_lab_inventory_response

router = APIRouter(prefix="/lab", tags=["lab"])


@router.get("/inventory")
def get_lab_inventory():
    return build_lab_inventory_response()
