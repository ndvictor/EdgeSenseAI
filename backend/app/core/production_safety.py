from __future__ import annotations

import os
from urllib.parse import urlparse


LOCAL_DATABASE_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def runtime_environment() -> str:
    return (os.environ.get("ENVIRONMENT") or os.environ.get("APP_ENV") or "dev").strip().lower()


def is_production_environment() -> bool:
    return runtime_environment() in {"prod", "production"}


def database_url_from_env() -> str:
    return (os.environ.get("DATABASE_URL") or "").strip()


def is_local_database_url(database_url: str | None) -> bool:
    if not database_url:
        return False
    try:
        parsed = urlparse(database_url)
    except Exception:
        return False
    host = (parsed.hostname or "").strip().lower()
    return host in LOCAL_DATABASE_HOSTS


def production_database_blocker(database_url: str | None = None) -> str | None:
    if not is_production_environment():
        return None
    raw = database_url_from_env() if database_url is None else str(database_url or "").strip()
    if not raw or is_local_database_url(raw):
        return "database_unavailable_or_misconfigured"
    return None


def allow_mock_market_data() -> bool:
    """Mock/demo market payloads are opt-in. Production never allows them."""
    if is_production_environment():
        return False
    return _truthy(os.environ.get("ALLOW_MOCK_MARKET_DATA"))


def allow_synthetic_market_data() -> bool:
    raw = os.environ.get("ALLOW_SYNTHETIC_MARKET_DATA")
    if raw is None:
        return not is_production_environment()
    return _truthy(raw)


def allow_worker_symbols_in_production() -> bool:
    """When false (default), WORKER_SYMBOLS must not seed scheduled production discovery/hydration."""
    return _truthy(os.environ.get("ALLOW_WORKER_SYMBOLS_IN_PRODUCTION"))
