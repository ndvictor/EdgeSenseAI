# Environment variables (backend, Azure dev)

This lists backend environment variables for the **Azure Container Apps dev backend** setup.

## Required

- **`DATABASE_URL`**: Supabase Postgres connection string.
- **`PORT`**: backend listen port (Azure injects this; default is `8900`).
- **`CORS_ORIGINS`**: allow your local frontend origin(s). For local-only frontend: `http://localhost:3000`.

## Required safety defaults (dev)

Set these explicitly for dev:

- `WORKFLOW_ENABLED=true`
- `PAPER_TRADING_ENABLED=true`
- `LIVE_TRADING_ENABLED=false`
- `BROKER_EXECUTION_ENABLED=false`
- `QLIB_EXECUTION_ENABLED=false`
- `REQUIRE_HUMAN_APPROVAL=true`

## Optional (should not be required for startup)

- **Redis**: `REDIS_URL`
- **Market data providers**
  - Alpaca: `ALPACA_MARKET_DATA_ENABLED`, `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `ALPACA_BASE_URL`
  - Polygon: `POLYGON_API_KEY`
  - Others: `TIINGO_API_KEY`, `ALPHA_VANTAGE_KEY`, `IEX_CLOUD_KEY`, `FRED_API_KEY`
- **News providers**
  - `NEWS_PROVIDER_ENABLED`, `NEWS_PROVIDER_PRIMARY`, `NEWS_PROVIDER_PRIORITY`
  - `NEWS_API_KEY`, `FINNHUB_API_KEY`, `BENZINGA_API_KEY`
- **LLM / embeddings (kept disabled/placeholder unless configured)**
  - `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`
  - `LITELLM_API_BASE`, `LITELLM_MASTER_KEY`
  - `EMBEDDINGS_PROVIDER`, `EMBEDDINGS_MODEL`, `EMBEDDINGS_ENABLE_PAID_CALLS`
- **Tracing**
  - `LANGSMITH_TRACING` and related LangSmith env vars (if used)

