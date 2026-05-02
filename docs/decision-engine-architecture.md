# EdgeSenseAI Decision Engine Architecture

This document describes how EdgeSenseAI should move from placeholder dashboards into a real small-account trading decision engine.

## Product Standard

The platform should not provide vague market speculation. Every promoted recommendation must answer:

- What is the action?
- What is the confidence?
- What is the current price?
- What is the buy zone?
- What is the stop?
- What is the target?
- What is the reward/risk?
- What is the account-sized position?
- What models support the decision?
- What invalidates the trade?

Until live market data and trained models are connected, the app must clearly mark outputs as `synthetic_prototype` or `research_only`.

## Current Service Layout

```text
backend/app/data_providers/
  base.py
  mock_provider.py
  provider_factory.py

backend/app/services/
  recommendation_engine_service.py
  edge_signal_service.py
  live_watchlist_service.py
  model_status_service.py
  feature_engineering_service.py
  account_feasibility_service.py
  risk_engine_service.py
  model_pipeline_service.py
```

## Decision Flow

```text
Market Snapshot
↓
Feature Engineering
↓
Model Pipeline
↓
Account Feasibility
↓
Risk Check
↓
Recommendation Engine
↓
Command Center Top Action
```

## Data Provider Layer

The data provider layer normalizes market data before it reaches the rest of the platform.

Current provider:

```text
MockMarketDataProvider
```

Future providers:

```text
PolygonProvider
AlpacaProvider
TradierProvider
CryptoProvider
```

Normalized snapshot fields:

```text
symbol
asset_class
current_price
previous_close
day_change_percent
volume
relative_volume
bid
ask
spread_percent
vwap
volatility_proxy
data_mode
```

## Feature Engineering Layer

The feature layer currently produces deterministic prototype scores:

```text
momentum_score
rvol_score
spread_quality_score
trend_vs_vwap_score
volatility_score
composite_feature_score
```

Future feature additions:

- candle returns
- rolling volatility
- ATR
- VWAP deviation
- order book imbalance
- options IV / OI / volume
- sector relative strength
- market breadth
- BTC funding / liquidation pressure
- sentiment spikes

## Statistical Model Layer

The intended model stack is:

```text
ARIMAX Directional Forecast
Kalman Trend Filter
GARCH Volatility Fit
HMM Regime Filter
XGBoost / LightGBM Meta-Ranker
```

Models should not directly place trades. They produce independent evidence. The recommendation engine combines that evidence with feature scores, account feasibility, and risk filters.

## Account Feasibility Layer

Small-account feasibility is applied before final ranking.

Possible outputs:

```text
feasible_direct_or_fractional
needs_fractional_or_smaller_size
watch_only_or_defined_risk_option
```

This prevents the platform from recommending trades that are technically interesting but impossible or dangerous for a $1K to $10K account.

## Risk Engine Layer

Risk checks include:

```text
reward_risk_ratio
max_dollar_risk
stop_distance_percent
risk_status
blockers
```

A recommendation should not be promoted if reward/risk, stop distance, or account risk constraints fail.

## Frontend Surfaces

### Command Center

Shows the top actionable recommendation:

```text
symbol
action label
confidence
current price
buy zone
stop
target
position size
max risk
model evidence
invalidation rules
```

### Live Watchlist

Shows monitored candidates plus readiness:

```text
market snapshot
feature score
model ranker score
account feasibility
risk status
next action
```

### Edge Signals

Shows fast-decay signal validation gates:

```text
spread pass
liquidity pass
regime pass
account fit
```

### Settings

Shows model readiness and next steps for ARIMAX, Kalman, GARCH, HMM, and XGBoost.

## API Endpoints

```text
GET /api/command-center
GET /api/live-watchlist/latest
GET /api/edge-signals/latest
GET /api/models/status
GET /api/market/snapshots
GET /api/features/{symbol}
GET /api/model-pipeline/{symbol}
GET /api/account-feasibility/{symbol}
GET /api/risk-check/{symbol}
```

## Next Implementation Priorities

1. Replace mock provider with a live provider adapter.
2. Persist account profile and watchlist state.
3. Build actual feature pipeline from candle and volume data.
4. Implement ARIMAX, Kalman, GARCH, and HMM services behind the current contract.
5. Create a backtest labeling service.
6. Train a ranker using backtest outcomes.
7. Add paper trade tracking and journal feedback loop.
