from typing import Any

import threading

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
        with _init_lock:
            if not _schema_initialized:
                Base.metadata.create_all(bind=engine)
                _schema_initialized = True
                health = check_database_health()
                return {"status": "configured", "created": True, **health}
        return {"status": "configured", "created": False, "message": "Schema already ensured for this process."}
    except Exception as exc:
        return {"status": "unavailable", "created": False, "message": str(exc)}
