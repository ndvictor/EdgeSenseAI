import os
import threading
import time
from collections.abc import Generator
from functools import lru_cache
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.settings import settings


# Cache the most recent health verdict so repeated checks (per-stage persistence
# in the orchestrator, etc.) don't pay multi-second connect timeouts each call
# when Postgres is unreachable. The cache is short-lived so a recovered DB is
# picked up on the next probe.
_HEALTH_CACHE_LOCK = threading.Lock()
_HEALTH_CACHE: dict[str, Any] = {"value": None, "expires_at": 0.0}


def _health_cache_ttl_seconds() -> float:
    raw = os.environ.get("DB_HEALTH_CACHE_TTL_SECONDS")
    try:
        if raw is not None:
            return max(0.0, float(raw))
    except ValueError:
        pass
    return 30.0


@lru_cache
def get_engine() -> Engine | None:
    if not settings.database_url:
        return None
    try:
        connect_args = {"connect_timeout": 1} if settings.database_url.startswith("postgresql") else {}
        return create_engine(settings.database_url, pool_pre_ping=True, pool_size=5, max_overflow=5, connect_args=connect_args)
    except Exception:
        return None


@lru_cache
def get_session_factory() -> sessionmaker[Session] | None:
    engine = get_engine()
    if engine is None:
        return None
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db_session() -> Generator[Session, None, None]:
    session = open_session()
    if session is None:
        return
    try:
        yield session
    finally:
        session.close()


def open_session() -> Session | None:
    factory = get_session_factory()
    if factory is None:
        return None
    cached = _HEALTH_CACHE.get("value") if isinstance(_HEALTH_CACHE.get("value"), dict) else None
    if cached is not None and not cached.get("connected") and time.monotonic() < float(_HEALTH_CACHE.get("expires_at") or 0.0):
        return None
    try:
        return factory()
    except Exception:
        return None


def _check_db_with_timeout(engine, timeout: float = 3.0) -> dict[str, Any]:
    """Check DB health with explicit timeout to prevent hanging."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            pgvector = connection.execute(text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")).scalar()
        return {"status": "connected", "connected": True, "pgvector_status": "enabled" if pgvector else "not_enabled", "message": "Postgres connection is healthy."}
    except SQLAlchemyError as exc:
        return {"status": "unavailable", "connected": False, "pgvector_status": "unknown", "message": str(exc)}
    except Exception as exc:
        return {"status": "unavailable", "connected": False, "pgvector_status": "unknown", "message": str(exc)}


def check_database_health(*, force_refresh: bool = False) -> dict[str, Any]:
    ttl = _health_cache_ttl_seconds()
    now = time.monotonic()
    if not force_refresh and ttl > 0:
        with _HEALTH_CACHE_LOCK:
            cached = _HEALTH_CACHE.get("value")
            if cached is not None and now < float(_HEALTH_CACHE.get("expires_at") or 0.0):
                return dict(cached)

    engine = get_engine()
    if engine is None:
        result: dict[str, Any] = {
            "status": "not_configured",
            "connected": False,
            "message": "DATABASE_URL is not configured or engine creation failed.",
        }
    else:
        result = _check_db_with_timeout(engine, timeout=3.0)

    if ttl > 0:
        with _HEALTH_CACHE_LOCK:
            _HEALTH_CACHE["value"] = dict(result)
            _HEALTH_CACHE["expires_at"] = now + ttl
    return result


def reset_database_health_cache() -> None:
    """Test/operational hook to clear the cached health verdict."""
    with _HEALTH_CACHE_LOCK:
        _HEALTH_CACHE["value"] = None
        _HEALTH_CACHE["expires_at"] = 0.0
