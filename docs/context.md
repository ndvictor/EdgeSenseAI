# EdgeSenseAI Project Continuation Context

This document captures the current EdgeSenseAI product direction, repo state, architecture, design goals, and next implementation steps so another chat or coding agent can continue without losing context.

## Product Summary

EdgeSenseAI is a focused small-account trading intelligence platform for traders starting with approximately $1,000 to $10,000 buying power.

It should not feel like a manual dashboard where the user has to click around and figure everything out. The product should be agent-driven:

- agents monitor the market continuously,
- agents detect urgent edge signals,
- agents perform feature engineering,
- statistical and ML models rank candidates,
- the account-risk layer validates feasibility,
- the platform notifies the user when a high-priority opportunity is worth attention.

The platform is research and paper-trading first. No live execution by default.

## Asset Focus

Only focus on:

1. Stocks
2. Options
3. Bitcoin / Crypto

Do not prioritize Gold, Commodities, Hedging Engine, Market Impact Radar, Recommendation Lifecycle, Agent Debate, or Admin right now.

## Trading Horizons

Stocks:

- Day trade
- Swing
- 1 month

Options:

- Day trade
- Swing
- 1 month
- Earnings plays

Bitcoin / Crypto:

- Intraday
- Swing
- 1 month / cycle context

## Local Development Ports

Avoid conflicts with other projects:

- OpsenseAI uses frontend 3000 and backend 8000
- TradeSenseAI uses frontend 3800 and backend 8800

EdgeSenseAI should use:

- Frontend: 3900
- Backend: 8900
- Future local Postgres: 55532
- Future local Redis: 56390

## Current Repo

Repository:

```text
ndvictor/EdgeSenseAI
```

The repo was initialized as a focused starter instead of a full direct copy of TradeSenseAI to avoid pulling over unused modules and old routing/Prisma problems.

Current structure:

```text
README.md
package.json

docs/
  context.md

backend/
  requirements.txt
  app/
    main.py
    schemas.py

frontend/
  package.json
  next.config.ts
  tsconfig.json
  postcss.config.mjs
  src/
    app/
      layout.tsx
      globals.css
      page.tsx
      command-center/page.tsx
      account-risk/page.tsx
      live-watchlist/page.tsx
      edge-signals/page.tsx
      stocks/page.tsx
      options/page.tsx
      crypto/page.tsx
      market-regime/page.tsx
      backtesting/page.tsx
      paper-trading/page.tsx
      journal/page.tsx
      settings/page.tsx
    components/
      AppShell.tsx
      Sidebar.tsx
      Cards.tsx
      PlaceholderPage.tsx
    lib/
      api.ts
```

## Important Recent Fixes

### Tailwind styling issue

The frontend originally rendered as plain HTML because Tailwind/PostCSS config was missing. This was fixed by adding:

```text
frontend/postcss.config.mjs
```

with:

```js
const config = {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};

export default config;
```

### Home page and dashboard shell issue

The initial root layout wrapped every route, including `/`, with the dashboard sidebar. The user wants `/` to be a real home/landing page, not straight dashboard.

The fix started by adding:

```text
frontend/src/components/AppShell.tsx
```

and updating:

```text
frontend/src/app/layout.tsx
```

to use the route-aware shell.

Intent:

- `/` should be a clean marketing/home page with no sidebar.
- App routes like `/command-center`, `/live-watchlist`, `/edge-signals`, etc. should show the dashboard sidebar.

Next chat should verify this behavior.

## Current Sidebar Target

The dashboard sidebar should contain only:

```text
Account Risk Center
Command Center
Live Watchlist
Edge Signals
Stocks
Options
Bitcoin / Crypto
Market Regime
Backtesting
Paper Trading
Journal
Settings
```

## Current Backend Endpoints

Current FastAPI backend endpoints:

```text
GET  /health
GET  /api/account-risk/profile
PUT  /api/account-risk/profile
GET  /api/live-watchlist/latest
POST /api/live-watchlist/scan
GET  /api/edge-signals/latest
POST /api/edge-signals/scan
GET  /api/command-center
```

Current backend is deterministic V1 structured data. That is okay for starter UI, but later logic should move out of `main.py` into services and real routes.

## Current Page Purpose

### `/`

Should become a premium landing/home page.

Target sections:

- EdgeSenseAI hero headline,
- small-account edge intelligence value proposition,
- agent-driven live alerts explanation,
- cards for Live Watchlist, Edge Signals, Recommendations,
- CTA to open Command Center,
- paper/research-only disclaimer,
- no sidebar.

### `/command-center`

Executive cockpit.

Should show:

- urgent edge alerts,
- top recommendations,
- buying power/account risk summary,
- portfolio snapshot later,
- recent agent activity later,
- cost usage later,
- no raw diagnostic clutter.

### `/account-risk`

Source of truth for:

- account equity,
- buying power,
- cash,
- max risk per trade,
- max daily loss,
- max position size,
- minimum reward/risk,
- small-account risk style.

Everything downstream should use this profile.

### `/live-watchlist`

Agent-driven watchlist that updates at a selected interval.

Purpose:

- show agents are continuously scanning,
- show candidates ranked by priority,
- show account feasibility,
- show notification status.

### `/edge-signals`

Urgent small-account edge signals.

Live Watchlist means what deserves attention. Edge Signals means what requires urgent alert because the signal decays quickly.

### `/stocks`

Focused stock workflows:

- day trade,
- swing,
- 1 month.

### `/options`

Focused options workflows:

- day trade,
- swing,
- 1 month,
- earnings plays.

### `/crypto`

Focused Bitcoin/Crypto workflows:

- intraday,
- swing,
- 1 month/cycle.

### `/market-regime`

Regime context:

- VIX,
- SPY/QQQ trend,
- sector context,
- Bitcoin risk-on/risk-off relationship,
- HMM regime state eventually.

### `/backtesting`

Future walk-forward validation and weight optimizer.

### `/paper-trading`

Paper validation. No live execution.

### `/journal`

Learning loop for outcomes and agent scorecards.

### `/settings`

Data source configuration, model readiness, alert settings, safety settings.

## Core Product Workflow

The intended workflow:

```text
Live Data Feeds
↓
Data Quality Agent
↓
Fast Edge Signal Agents
↓
Core Feature Engineering Agents
↓
Time-Series Prediction Models
↓
Volatility + Regime Models
↓
XGBoost / LightGBM Meta-Ranking
↓
Dynamic Weighting Layer
↓
Account Feasibility Pre-Check
↓
Risk / Liquidity / Spread Filter
↓
Agent Committee Review
↓
Final Recommendation
↓
Alert / Notification / Paper Trade Candidate
```

Important product mindset:

```text
Agents work for the user.
Agents watch the market.
Agents notify when an edge appears.
The risk layer prevents bad trades.
The recommendation engine only shows validated opportunities.
```

Avoid designing only manual scan buttons.

## Key Design Principle

Models do not directly recommend a stock or option.

Models generate independent signals. The platform combines, ranks, risk-adjusts, account-filters, and then recommends.

Professional-style pipeline:

```text
Market Event
↓
Dynamic Watchlist
↓
Account Feasibility
↓
Statistical Signals
↓
Meta-Model Ranking
↓
Risk Filters
↓
Agent Committee
↓
Top Recommendations
```

## Small-Account Edge Signals

The user believes many useful trading signals only work because the account is small. As size increases, market impact, liquidity, and competition destroy the edge.

Priority edge signals:

1. Order book imbalance / microstructure
2. Low-float / low-liquidity breakouts
3. Unusual volume spikes / RVOL
4. Short-term mean reversion, especially 1-5 minutes
5. Retail sentiment spikes
6. Simple options flow signals
7. ETF vs stock lag / pairs / arbitrage-lite
8. Short-term momentum
9. Breakouts
10. Advanced options flow
11. Regime shifts
12. Crypto funding/liquidation/volatility shock

Frequency context:

- Order book imbalance: many times daily, lasts seconds to 2 minutes
- Low-float breakout: few times per week, lasts 5-60 minutes
- RVOL spike: daily, lasts 5-30 minutes
- 1-5 min mean reversion: many times daily, lasts 1-10 minutes
- Retail sentiment spike: few times per week, lasts 30 minutes to 2 days
- Unusual calls/puts: daily, lasts 15 minutes to 1 day
- ETF vs stock lag: several daily, lasts seconds to 10 minutes
- Short-term momentum: daily, lasts 5-60 minutes
- Breakouts: daily, lasts 10 minutes to several hours
- Advanced options flow: daily, lasts 30 minutes to several days
- Regime shift: few times per week/month, lasts hours to weeks

Rule:

```text
Fast edge signal → confirm with volume + spread + regime → score → alert
```

Do not let a signal alone trigger action.

## Edge Signal Filters

No urgent edge signal should alert by itself.

It should pass:

- spread filter,
- liquidity filter,
- regime filter,
- false-breakout filter,
- account-risk filter.

Edge Signal scoring:

```text
Raw Signal Score
× Regime Multiplier
× Liquidity Multiplier
× Spread Multiplier
× Volatility Multiplier
× Confidence Multiplier
= Final Edge Score
```

Example output:

```json
{
  "symbol": "NVDA",
  "asset_class": "stock",
  "signal_name": "RVOL + Breakout",
  "urgency": "high",
  "time_decay": "5-30 min",
  "confidence": 0.78,
  "account_fit": "needs_smaller_expression",
  "recommended_action": "Watch for pullback or defined-risk option spread",
  "alert_status": "sent"
}
```

## Model Stack

Core statistical and ML model stack:

- ARIMAX: directional baseline with external variables
- VAR: relationships across stock/index/sector/VIX/BTC
- Kalman Filter: adaptive trend and mean reversion
- GARCH / EGARCH / GARCH-X: volatility clustering and volatility forecast
- HMM: market regime detection
- XGBoost / LightGBM: nonlinear ranking and probability scoring
- Ensemble: final score smoothing and multi-signal combination

## Models by Asset and Horizon

### Stocks Day Trading

Models:

- ARIMAX
- Kalman Filter
- GARCH
- XGBoost

Features:

- VWAP deviation
- RVOL
- bid/ask spread
- 1m / 5m / 15m momentum
- order book imbalance
- news shock
- breakout score
- mean reversion score

Agents:

- Market Data Agent
- Technical Agent
- Volume Agent
- News Agent
- Volatility Agent
- Risk Agent

### Stocks Swing Trading

Models:

- ARIMAX
- VAR
- GARCH
- HMM
- XGBoost

Features:

- RSI
- MACD
- 5-20 day momentum
- sector relative strength
- options flow
- sentiment
- breakout confirmation

Agents:

- Technical Agent
- Options Agent
- Sentiment Agent
- Sector/Macro Agent
- Regime Agent
- Risk Agent

### Stocks 1 Month

Models:

- VAR
- ARIMAX
- GARCH
- XGBoost / LightGBM

Features:

- MA20 / MA50
- relative strength
- earnings revisions
- IV rank
- sector trend
- macro regime

### Options Day Trading

Models:

- GARCH
- EGARCH
- XGBoost
- Kalman Filter

Features:

- IV change
- delta flow
- gamma exposure
- unusual volume
- spread
- underlying momentum
- bid/ask quality

Agents:

- Options Flow Agent
- Volatility Agent
- Technical Agent
- Liquidity Agent
- Risk Agent

### Options Swing

Models:

- ARIMAX
- GARCH
- HMM
- XGBoost

Features:

- IV rank
- skew
- term structure
- put/call ratio
- OI change
- underlying trend

### Options Earnings Play

Models:

- GARCH
- Event Classifier
- XGBoost
- Logistic Regression

Features:

- IV crush risk
- expected move
- IV vs realized volatility
- earnings surprise history
- sentiment
- gap history

Small-account options rule:

Prefer defined-risk debit spreads, small premium trades, and watch-only alerts. Avoid wide bid/ask contracts, low open interest, high IV crush setups, and oversized premium risk.

### Bitcoin / Crypto Intraday

Models:

- ARIMAX
- Kalman Filter
- GARCH
- XGBoost

Features:

- funding rate
- liquidations
- order book imbalance
- perp volume
- BTC dominance
- momentum
- volatility burst

Agents:

- Crypto Data Agent
- Derivatives Agent
- Volume Agent
- Technical Agent
- Risk Agent

### Bitcoin / Crypto Swing

Models:

- VAR
- ARIMAX
- HMM
- XGBoost

Features:

- momentum
- funding trend
- open interest
- exchange flows
- sentiment
- macro risk-on/off

### Bitcoin / Crypto 1 Month

Models:

- VAR
- HMM
- XGBoost
- Ensemble

Features:

- ETF flows
- liquidity
- BTC dominance
- longer trend
- volatility regime

## Agent Architecture

Agents produce features, explanations, risk objections, and alerts. Agents should not independently pick trades without model/risk validation.

Data and ingestion agents:

- Market Data Agent
- Options Data Agent
- Crypto Data Agent
- News/Sentiment Agent
- Macro Agent
- Data Quality Agent

Edge signal agents:

- Level 2 Microstructure Agent
- Low-Float Breakout Agent
- RVOL Spike Agent
- Short-Term Reversion Agent
- Retail Sentiment Agent
- Unusual Options Agent
- Relative Lag Agent
- Momentum Agent
- Breakout Agent
- Advanced Options Agent
- Regime Agent
- Crypto Derivatives Agent

Feature engineering agents:

- Technical Feature Agent
- Volume Feature Agent
- Options Feature Agent
- Sentiment Feature Agent
- Macro Feature Agent
- Volatility Feature Agent
- Liquidity Feature Agent
- Regime Feature Agent

Decision agents:

- Risk Agent
- Account Feasibility Agent
- Options Structure Agent
- Crypto Risk Agent
- Journal Agent
- CIO Agent

Core rule:

```text
Agents produce features.
Models rank.
Risk filter validates.
Final engine recommends.
```

## Backtesting and Weight Optimization

The user wants backtesting to iterate weights and find the best prediction/ranking strategy.

Do not optimize only for accuracy.

Track:

- win rate,
- expectancy per trade,
- average R,
- profit factor,
- max drawdown,
- Sharpe,
- Sortino,
- target-before-stop rate,
- false positive rate,
- account survivability.

Winner labels by horizon:

- Day trade: target hit before stop within same day.
- Swing: target hit before stop within 3-10 trading days.
- 1 month: forward return exceeds threshold and max drawdown stays controlled.
- Options: option/spread reaches profit target before max loss or expiration.

Use walk-forward validation:

```text
Train window → validation window → roll forward → repeat
```

Future services:

```text
backend/app/services/backtest_weight_optimizer_service.py
backend/app/services/backtest_labeling_service.py
backend/app/services/backtest_metrics_service.py
```

Future endpoints:

```text
POST /api/backtest/optimize-weights
GET  /api/backtest/weight-profiles
POST /api/backtest/evaluate-profile
```

## Account Feasibility Logic

Buying power should be introduced early, not only at the end.

Workflow:

```text
Market Trigger Engine
↓
Dynamic Watchlist Builder
↓
Account Feasibility Pre-Check
↓
Expression Router
↓
Statistical Signal Engine
↓
Account-Aware Scanner
↓
Agent Committee
↓
Final Recommendation
```

Account feasibility should route opportunities instead of deleting everything:

- feasible,
- needs smaller expression,
- watch only,
- blocked.

For a $1K-$10K account, high-priced stocks may need fractional shares, ETF proxy, defined-risk option spread, or watch-only alert.

## Recommendation Output Format

Final recommendations should include:

```text
symbol
asset_class
horizon
final_decision
final_score
confidence
entry
stop
target
max_position_size
buying_power_required
max_dollar_risk
reward_risk_ratio
expected_R
model_stack
reason
risk_factors
invalidation_rules
```

## Command Center Target Layout

Command Center should show:

- Urgent Edge Alerts
- Top Recommendations
- Buying Power & Risk Profile
- Portfolio Snapshot
- Portfolio Risk
- Recent Agent Activity
- Cost Usage

For now it can show account metrics, urgent edge alerts, and top recommendations.

## Live Watchlist Target Layout

Live Watchlist should show:

- live status,
- auto-refresh interval,
- notify toggle,
- agent status strip,
- live candidates table,
- triggered now,
- high-conviction count,
- alerts sent today,
- research-only/no live execution disclaimer.

## Edge Signals Target Layout

Edge Signals page should show:

- signal name,
- asset,
- symbol,
- urgency,
- time decay,
- confidence,
- spread/liquidity pass,
- regime pass,
- account fit,
- recommended action,
- alert status.

## Settings Target Layout

Settings should eventually include:

- data readiness,
- provider status,
- market data source configuration,
- options data status,
- crypto data status,
- model readiness,
- alert settings,
- safety settings,
- paper-only mode.

## Immediate Next Steps

1. Pull latest repo.
2. Verify frontend CSS and shell.
3. Confirm `/` has no sidebar.
4. Build a premium EdgeSenseAI home page.
5. Improve dashboard visual quality.
6. Refactor backend logic out of `main.py` into services and route modules:
   - `edge_signal_service.py`
   - `live_watchlist_service.py`
   - `account_feasibility_service.py`
   - `statistical_model_service.py`
   - `meta_ranking_service.py`
7. Add tests for health, account risk, live watchlist, edge signals, and command center.

## Run Commands

Pull:

```bash
cd ~/projects/EdgeSenseAI
git fetch origin
git pull origin main
```

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8900 --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:3900
```

API:

```text
http://localhost:8900/health
http://localhost:8900/api/command-center
http://localhost:8900/api/live-watchlist/latest
http://localhost:8900/api/edge-signals/latest
```

## Dependency Notes

Backend requirements were aligned with TradeSenseAI so the user does not need to install missing packages one by one.

Frontend package dependencies were also aligned with TradeSenseAI and include Next, React, Tailwind, lucide-react, framer-motion, lightweight-charts, react-icons, tailwind-merge, Prisma packages, next-auth, OpenAI package, and related tooling.

## Best Continuation Prompt

Use this prompt in a new chat:

```text
Read docs/context.md in the EdgeSenseAI repo. Continue from there. First verify the frontend shell and home page. Then make the home page premium and route-aware so `/` has no sidebar, while app pages keep the dashboard sidebar. After that, refactor backend logic out of main.py into live_watchlist_service.py, edge_signal_service.py, and account_feasibility_service.py. Keep ports frontend 3900 and backend 8900. Focus only on Stocks, Options, and Bitcoin/Crypto for $1K-$10K accounts.
```
