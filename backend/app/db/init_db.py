from typing import Any

from app.db.models import Base
from app.db import research_models  # noqa: F401 - registers research/promotion tables on Base.metadata
from app.db.session import check_database_health, get_engine


def init_db() -> dict[str, Any]:
    engine = get_engine()
    if engine is None:
        return {"status": "not_configured", "created": False, "message": "No database engine available."}
    try:
        Base.metadata.create_all(bind=engine)
        health = check_database_health()
        return {"status": "configured", "created": True, **health}
    except Exception as exc:
        return {"status": "unavailable", "created": False, "message": str(exc)}
