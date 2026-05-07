from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_inputs_hash(*, agent_key: str, workflow_run_id: str, inputs: dict, context: dict, requested_stage: int | None, idempotency_key: str | None) -> str:
    payload: dict[str, Any] = {
        "agent_key": agent_key,
        "workflow_run_id": workflow_run_id,
        "inputs": inputs,
        "context": context,
        "requested_stage": requested_stage,
        "idempotency_key": idempotency_key,
    }
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def fingerprint(*, agent_key: str, workflow_run_id: str, inputs: dict, context: dict, requested_stage: int | None, idempotency_key: str | None) -> str:
    # Fingerprint is derived from the stable hash to keep indexing compact.
    return stable_inputs_hash(
        agent_key=agent_key,
        workflow_run_id=workflow_run_id,
        inputs=inputs,
        context=context,
        requested_stage=requested_stage,
        idempotency_key=idempotency_key,
    )

