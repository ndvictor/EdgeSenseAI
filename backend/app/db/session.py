import concurrent.futures
from collections.abc import Generator
from functools import lru_cache
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.settings import settings


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
    factory = get_session_factory()
    if factory is None:
        return
    session = factory()
    try:
        yield session
    finally:
        session.close()


def open_session() -> Session | None:
    factory = get_session_factory()
    if factory is None:
        return None
    try:
        return factory()
    except Exception:
        return None


def _check_db_with_timeout(engine, timeout: float = 3.0) -> dict[str, Any]:
    """Check DB health with explicit timeout to prevent hanging."""
    def _check():
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            pgvector = connection.execute(text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")).scalar()
        return {"status": "connected", "connected": True, "pgvector_status": "enabled" if pgvector else "not_enabled", "message": "Postgres connection is healthy."}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_check)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            return {"status": "timeout", "connected": False, "pgvector_status": "unknown", "message": f"Connection timeout after {timeout}s"}
        except SQLAlchemyError as exc:
            return {"status": "unavailable", "connected": False, "pgvector_status": "unknown", "message": str(exc)}
        except Exception as exc:
            return {"status": "unavailable", "connected": False, "pgvector_status": "unknown", "message": str(exc)}


def check_database_health() -> dict[str, Any]:
    engine = get_engine()
    if engine is None:
        return {"status": "not_configured", "connected": False, "message": "DATABASE_URL is not configured or engine creation failed."}
    return _check_db_with_timeout(engine, timeout=3.0)
