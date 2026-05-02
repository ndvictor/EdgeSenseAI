from datetime import datetime

from app.core.settings import settings


def get_health_snapshot() -> dict:
    return {
        "status": "ok",
        "service": "edgesenseai-backend",
        "version": "0.7.0",
        "app_env": settings.app_env,
        "database_configured": bool(settings.database_url),
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
