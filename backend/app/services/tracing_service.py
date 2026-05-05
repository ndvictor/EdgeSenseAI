"""Lightweight tracing utility for LangSmith and structured logging.

Safe optional tracing without hard dependency on LangSmith.
"""

import os
from datetime import datetime, timezone
from typing import Any

from app.core.effective_runtime import effective_bool

# Lazy import - no hard dependency on langsmith
_LANGSMITH_AVAILABLE = None

def _is_langsmith_available() -> bool:
    global _LANGSMITH_AVAILABLE
    if _LANGSMITH_AVAILABLE is None:
        try:
            import langsmith  # noqa: F401
            _LANGSMITH_AVAILABLE = True
        except ImportError:
            _LANGSMITH_AVAILABLE = False
    return _LANGSMITH_AVAILABLE


def is_tracing_enabled() -> bool:
    """Check if LangSmith tracing is enabled."""
    if not effective_bool("LANGSMITH_TRACING"):
        return False
    if not os.environ.get("LANGSMITH_API_KEY"):
        return False
    if not os.environ.get("LANGSMITH_PROJECT"):
        return False
    return True


def get_tracing_status() -> dict[str, Any]:
    """Get detailed tracing status without exposing secrets."""
    tracing = effective_bool("LANGSMITH_TRACING")
    api_key_set = bool(os.environ.get("LANGSMITH_API_KEY"))
    project_set = bool(os.environ.get("LANGSMITH_PROJECT"))
    langsmith_installed = _is_langsmith_available()

    enabled = tracing and api_key_set and project_set and langsmith_installed

    return {
        "enabled": enabled,
        "configured": tracing and api_key_set and project_set,
        "langsmith_installed": langsmith_installed,
        "langsmith_tracing_env": tracing,
        "api_key_configured": api_key_set,
        "project_configured": project_set,
        "mode": "langsmith" if enabled else "no-op",
    }


def trace_event(
    name: str,
    inputs: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """Trace a single event. Returns True if tracing was active.

    Safe - does not crash if LangSmith is not available.
    Never exposes secrets in logged data.
    """
    status = get_tracing_status()

    # Always log structured event for observability
    event_data = {
        "event": name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tracing_enabled": status["enabled"],
        "inputs": inputs,
        "outputs": outputs,
        "metadata": _sanitize_metadata(metadata or {}),
    }

    # Log to stdout/stderr for capture by logging infrastructure
    print(f"[TRACE] {event_data}", flush=True)

    if not status["enabled"]:
        return False

    # Try to send to LangSmith if available
    if _is_langsmith_available():
        try:
            from langsmith import Client
            client = Client()
            # Run tree for the event
            run = client.create_run(
                name=name,
                run_type="chain",
                inputs=inputs or {},
                outputs=outputs or {},
                extra=_sanitize_metadata(metadata or {}),
            )
            return True
        except Exception:
            # Fail silently - tracing should not break functionality
            return False

    return False


def trace_workflow_step(
    workflow_name: str,
    step_name: str,
    status: str,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """Trace a workflow step.

    Standardized tracing for main workflow services.
    """
    event_name = f"{workflow_name}.{step_name}"
    return trace_event(
        name=event_name,
        outputs={"status": status},
        metadata={
            "workflow": workflow_name,
            "step": step_name,
            **(metadata or {}),
        },
    )


def _sanitize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Remove secrets and sensitive data from metadata."""
    sensitive_keys = {
        "api_key", "apikey", "api-key", "key", "secret", "password",
        "token", "auth", "credential", "private_key", "access_token",
        "LANGSMITH_API_KEY", "DATABASE_URL", "REDIS_URL", "ALPACA_API_KEY",
        "POLYGON_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
    }

    sanitized = {}
    for key, value in metadata.items():
        key_lower = key.lower()
        if any(s in key_lower for s in sensitive_keys):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_metadata(value)
        elif isinstance(value, list):
            sanitized[key] = [
                _sanitize_metadata(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            sanitized[key] = value

    return sanitized
