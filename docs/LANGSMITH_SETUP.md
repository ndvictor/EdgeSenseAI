# LangSmith Setup Guide

This guide explains how to set up LangSmith tracing for EdgeSenseAI to enable observability across workflow services.

## Overview

LangSmith tracing is **optional** and operates in a safe, no-op mode when not configured. When enabled, it traces:
- Workflow stage transitions (start, completion, errors)
- Service calls and their duration
- Key decision points (market regime, strategy ranking, etc.)
- Metadata (sanitized, no secrets)

## Prerequisites

1. **LangSmith Account**: Sign up at https://smith.langchain.com
2. **API Key**: Generate from your LangSmith account settings
3. **Project**: Create a project in LangSmith for this application

## Environment Variables

Add these to your `.env` file:

```bash
# Required for tracing
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_api_key_here
LANGSMITH_PROJECT=edgesenseai

# Optional: Endpoint (defaults to LangSmith cloud)
# LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

## Configuration

### 1. Install LangSmith (Optional)

LangSmith is an optional dependency. If you want tracing:

```bash
cd backend
pip install langsmith
```

Or add to `requirements.txt`:
```
langsmith>=0.1.0
```

### 2. Verify Configuration

Check if tracing is configured correctly:

```bash
cd backend
python -c "from app.services.tracing_service import get_tracing_status; print(get_tracing_status())"
```

Or use the platform readiness endpoint:
```bash
curl http://localhost:8000/api/tracing/status
```

## Testing

### Send a Test Tracing Event

```bash
curl -X POST http://localhost:8000/api/tracing/test-event \
  -H "Content-Type: application/json" \
  -d '{"name": "test_event", "metadata": {"test": true}}'
```

### Run a Workflow and Check Traces

1. Run any workflow (e.g., strategy ranking):
```bash
curl -X POST http://localhost:8000/api/strategy-ranking/run \
  -H "Content-Type: application/json" \
  -d '{
    "market_phase": "regular_hours",
    "active_loop": "regular_hours_analysis",
    "regime": "bullish",
    "horizon": "swing"
  }'
```

2. Check LangSmith dashboard for traces:
   - Visit https://smith.langchain.com
   - Navigate to your project
   - View traces under "Tracing"

## Tracing Scope

### Traced Workflow Stages

The following stages are traced in the Upper Workflow:
- Workflow start
- Data freshness check
- Market regime detection
- Strategy ranking
- Universe selection
- Meta-model ensemble
- Recommendation pipeline
- Workflow completion

### Metadata Included

Each trace includes:
- `workflow_id`: Unique workflow run ID
- `stage`: The workflow stage being traced
- `source`: Data source used
- `horizon`: Trading horizon
- `duration_ms`: Stage execution time
- `outcome`: Success/failure status

### Metadata NOT Included (Security)

- API keys
- Database URLs
- Credentials
- Secrets
- PII (Personal Identifiable Information)

## Disabling Tracing

To disable tracing, either:

1. **Remove environment variables**:
```bash
# Comment out or delete in .env
# LANGSMITH_TRACING=true
# LANGSMITH_API_KEY=...
```

2. **Set tracing to false**:
```bash
LANGSMITH_TRACING=false
```

When disabled, tracing calls become no-ops with zero overhead.

## Troubleshooting

### Tracing Not Working

1. **Check configuration**:
```bash
python check_platform_readiness.py --json | grep -A5 langsmith
```

2. **Verify API key**:
```bash
curl https://api.smith.langchain.com/runs \
  -H "x-api-key: $LANGSMITH_API_KEY"
```

3. **Check logs** for tracing errors (they're caught and logged as warnings)

### High Latency

Tracing adds minimal latency (~10-50ms per trace). If experiencing issues:
- Disable tracing in production: `LANGSMITH_TRACING=false`
- Tracing is already async/best-effort (errors don't block workflows)

### Missing Traces

Traces may not appear if:
- LangSmith API is temporarily unavailable
- API key is invalid
- Project name doesn't exist

Check `tracing_status` endpoint for configuration state.

## Development Tips

### Local Testing

Use the smoke test script with tracing enabled:
```bash
cd backend
python scripts/integration_smoke_test.py --enable-tracing
```

### CI/CD Integration

In CI environments, use test keys or disable tracing:
```bash
# .github/workflows/test.yml
LANGSMITH_TRACING=false
```

### Production Deployment

Recommended production settings:
```bash
# Only enable if you need observability
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=${LANGSMITH_API_KEY_SECRET}  # From secrets manager
LANGSMITH_PROJECT=edgesenseai-production
```

## Security Notes

1. **Never commit API keys** to version control
2. **Use environment variables** or secrets managers
3. **Metadata is sanitized** automatically (no secrets in traces)
4. **Tracing is optional** - platform works without it
5. **No PII** should be passed in trace metadata

## Additional Resources

- [LangSmith Documentation](https://docs.smith.langchain.com/)
- [LangSmith API Reference](https://api.smith.langchain.com/redoc)
- EdgeSenseAI Tracing Service: `backend/app/services/tracing_service.py`
