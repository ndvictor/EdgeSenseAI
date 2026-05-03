"""Tracing status and test endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.tracing_service import (
    get_tracing_status,
    trace_event,
)

router = APIRouter()


class TracingStatusResponse(BaseModel):
    enabled: bool
    configured: bool
    langsmith_installed: bool
    langsmith_tracing_env: bool
    api_key_configured: bool
    project_configured: bool
    mode: str


class TracingTestEventRequest(BaseModel):
    name: str = Field(default="test_event", description="Event name")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Optional metadata")


class TracingTestEventResponse(BaseModel):
    tracing_enabled: bool
    event_sent: bool
    event_name: str
    mode: str


@router.get("/tracing/status", response_model=TracingStatusResponse)
def get_tracing_status_endpoint():
    """Get LangSmith tracing status without exposing secrets."""
    status = get_tracing_status()
    return TracingStatusResponse(
        enabled=status["enabled"],
        configured=status["configured"],
        langsmith_installed=status["langsmith_installed"],
        langsmith_tracing_env=status["langsmith_tracing_env"],
        api_key_configured=status["api_key_configured"],
        project_configured=status["project_configured"],
        mode=status["mode"],
    )


@router.post("/tracing/test-event", response_model=TracingTestEventResponse)
def send_tracing_test_event(request: TracingTestEventRequest):
    """Send a test tracing event.

    Useful for validating tracing configuration without running full workflows.
    """
    status = get_tracing_status()
    event_sent = trace_event(
        name=request.name,
        metadata={
            "source": "manual_test",
            **request.metadata,
        },
    )

    return TracingTestEventResponse(
        tracing_enabled=status["enabled"],
        event_sent=event_sent,
        event_name=request.name,
        mode=status["mode"],
    )
