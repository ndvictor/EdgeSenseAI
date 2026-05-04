from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.services.research_persistence_service import (
    create_model_artifact,
    get_latest_valid_model_artifact,
    get_model_artifact,
    list_model_artifacts,
)


class ModelArtifactRegisterRequest(BaseModel):
    model_key: str
    artifact_version: str = "v0"
    artifact_type: str = "wrapper"
    artifact_uri: str | None = None
    artifact_hash: str | None = None
    provider: str | None = None
    source: str = "manual"
    status: str | None = None
    feature_version: str | None = None
    label_definition: str | None = None
    created_by: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def register_model_artifact(request: ModelArtifactRegisterRequest) -> dict[str, Any]:
    payload = request.model_dump()
    if not payload.get("artifact_uri") and not payload.get("artifact_hash") and not payload.get("status"):
        payload["status"] = "missing"
    return create_model_artifact(payload)


def list_artifacts(model_key: str | None = None) -> dict[str, Any]:
    return {"data_source": "postgres_or_empty", "artifacts": list_model_artifacts(model_key)}


def get_artifact(artifact_id: str) -> dict[str, Any]:
    artifact = get_model_artifact(artifact_id)
    return artifact or {"id": artifact_id, "status": "not_found", "data_source": "postgres_or_empty"}


def latest_artifact(model_key: str) -> dict[str, Any]:
    artifact = get_latest_valid_model_artifact(model_key)
    return artifact or {"model_key": model_key, "status": "missing", "data_source": "postgres_or_empty", "next_action": "Register a real artifact or wrapper before evaluation/promotion."}
