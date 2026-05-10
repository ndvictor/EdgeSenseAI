from typing import Any

import threading

from app.core.production_safety import is_production_environment
from app.db.models import Base
from app.db import research_models  # noqa: F401 - registers research/promotion tables on Base.metadata
from app.db.session import check_database_health, get_engine

_init_lock = threading.Lock()
_schema_initialized = False


def init_db() -> dict[str, Any]:
    global _schema_initialized
    engine = get_engine()
    if engine is None:
        return {"status": "not_configured", "created": False, "message": "No database engine available."}
    try:
        health = check_database_health()
        if not health.get("connected"):
            return {"created": False, **health}
        with _init_lock:
            if not _schema_initialized:
                if is_production_environment():
                    _schema_initialized = True
                    return {"status": "configured", "created": False, "message": "Production schema initialization is managed outside request handling.", **health}
                Base.metadata.create_all(bind=engine)
                _schema_initialized = True
                return {"status": "configured", "created": True, **health}
        return {"status": "configured", "created": False, "message": "Schema already ensured for this process."}
    except Exception as exc:
        return {"status": "unavailable", "created": False, "message": str(exc)}
