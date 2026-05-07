from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.settings import settings


@dataclass(frozen=True)
class RedisRuntimeStatus:
    redis_mode: str  # "available" | "unavailable" | "disabled"
    message: str


def _get_client():
    """Return a redis client if available; otherwise None. Never raises."""
    if not getattr(settings, "redis_url", None):
        return None
    try:
        import redis  # type: ignore

        return redis.Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=1,
            socket_timeout=1,
            decode_responses=True,
        )
    except Exception:
        return None


def get_redis_runtime_status() -> RedisRuntimeStatus:
    if not getattr(settings, "redis_url", None):
        return RedisRuntimeStatus(redis_mode="disabled", message="REDIS_URL not configured.")
    client = _get_client()
    if client is None:
        return RedisRuntimeStatus(redis_mode="unavailable", message="Redis client unavailable (package missing or init failed).")
    try:
        client.ping()
        return RedisRuntimeStatus(redis_mode="available", message="Redis reachable.")
    except Exception as exc:
        return RedisRuntimeStatus(redis_mode="unavailable", message=str(exc))


def _lock_key(workflow_run_id: str, agent_key: str) -> str:
    return f"agent_runtime:lock:{workflow_run_id}:{agent_key}"


def acquire_agent_lock(*, workflow_run_id: str, agent_key: str, ttl_seconds: int = 60) -> bool:
    client = _get_client()
    if client is None:
        return False
    try:
        # SET key value NX EX ttl
        return bool(client.set(_lock_key(workflow_run_id, agent_key), "1", nx=True, ex=int(ttl_seconds)))
    except Exception:
        return False


def release_agent_lock(*, workflow_run_id: str, agent_key: str) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        client.delete(_lock_key(workflow_run_id, agent_key))
    except Exception:
        return


def _active_key(workflow_run_id: str) -> str:
    return f"agent_runtime:active_workflow:{workflow_run_id}"


def set_active_workflow_state(*, workflow_run_id: str, state: dict[str, Any], ttl_seconds: int = 3600) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        import json

        client.setex(_active_key(workflow_run_id), int(ttl_seconds), json.dumps(state, sort_keys=True, default=str))
    except Exception:
        return


def get_active_workflow_state(workflow_run_id: str) -> dict[str, Any] | None:
    client = _get_client()
    if client is None:
        return None
    try:
        import json

        raw = client.get(_active_key(workflow_run_id))
        if not raw:
            return None
        val = json.loads(raw)
        return val if isinstance(val, dict) else None
    except Exception:
        return None


def _idem_key(fingerprint: str) -> str:
    return f"agent_runtime:idempotency:{fingerprint}"


def set_idempotency_cache(*, fingerprint: str, run_id: str, ttl_seconds: int = 86400) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        client.setex(_idem_key(fingerprint), int(ttl_seconds), run_id)
    except Exception:
        return


def get_idempotency_cache(fingerprint: str) -> str | None:
    client = _get_client()
    if client is None:
        return None
    try:
        val = client.get(_idem_key(fingerprint))
        return str(val) if val else None
    except Exception:
        return None

