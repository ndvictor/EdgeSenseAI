from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AccountOwnerPolicyRequest(BaseModel):
    """Stage-1 policy check request.

    v1: optional context only; policy is derived from effective runtime gates.
    """

    model_config = ConfigDict(protected_namespaces=())

    workflow_run_id: str | None = None
    mode: str | None = None
    actor: str | None = None


class AccountOwnerPolicyResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    status: Literal["ok"]
    decision: Literal["allow", "blocked"]
    data_mode: Literal["effective_runtime_v1"] = "effective_runtime_v1"
    gates: dict = Field(default_factory=dict)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_action: str
    checked_at: str

