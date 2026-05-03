from datetime import datetime

from app.core.settings import settings
from app.services.embedding_service import get_embedding_status
from app.services.persistence_service import get_persistence_status
from app.services.vector_memory_service import get_vector_memory_status


def get_health_snapshot() -> dict:
    persistence = get_persistence_status()
    memory = get_vector_memory_status()
    return {
        "status": "ok",
        "service": "edgesenseai-backend",
        "version": "0.7.0",
        "app_env": settings.app_env,
        "database_configured": bool(settings.database_url),
        "postgres_persistence_status": persistence["postgres_persistence_status"],
        "pgvector_status": persistence["pgvector_status"],
        "embedding_provider": get_embedding_status()["provider"],
        "vector_memory_status": memory["vector_memory_status"],
        "redis_configured": bool(settings.redis_url),
        "market_data_provider": settings.market_data_provider,
        "market_data_provider_priority": settings.market_data_provider_priority,
        "live_trading_enabled": settings.live_trading_enabled,
        "paper_trading_enabled": settings.paper_trading_enabled,
        "execution_agent_enabled": settings.execution_agent_enabled,
        "require_human_approval": settings.require_human_approval,
        "backend_port": 8900,
        "frontend_port": 3900,
        "timestamp": datetime.utcnow().isoformat(),
    }
