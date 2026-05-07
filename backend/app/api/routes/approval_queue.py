from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.approval_queue.models import ApprovalActionRequest, ApprovalItemCreate
from app.services.approval_queue.service import approve_item, cancel_item, create_item, get_item, get_status, list_items, reject_item

router = APIRouter(prefix="/approval-queue", tags=["approval-queue"])


@router.get("/status")
def get_queue_status():
    return get_status().model_dump()


@router.get("/items")
def get_items(limit: int = 50, status: str | None = None):
    return {"status": "ok", "items": [i.model_dump() for i in list_items(limit=limit, status=status)]}


@router.get("/items/{approval_id}")
def get_item_route(approval_id: str):
    item = get_item(approval_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Approval item not found")
    return {"status": "ok", "item": item.model_dump()}


@router.post("/items")
def post_item(body: ApprovalItemCreate):
    item = create_item(body)
    return {"status": "ok", "item": item.model_dump()}


@router.post("/items/{approval_id}/approve")
def post_approve(approval_id: str, body: ApprovalActionRequest):
    item = approve_item(approval_id, body)
    if item is None:
        raise HTTPException(status_code=404, detail="Approval item not found")
    return {"status": "ok", "item": item.model_dump()}


@router.post("/items/{approval_id}/reject")
def post_reject(approval_id: str, body: ApprovalActionRequest):
    item = reject_item(approval_id, body)
    if item is None:
        raise HTTPException(status_code=404, detail="Approval item not found")
    return {"status": "ok", "item": item.model_dump()}


@router.post("/items/{approval_id}/cancel")
def post_cancel(approval_id: str, body: ApprovalActionRequest):
    item = cancel_item(approval_id, body)
    if item is None:
        raise HTTPException(status_code=404, detail="Approval item not found")
    return {"status": "ok", "item": item.model_dump()}

