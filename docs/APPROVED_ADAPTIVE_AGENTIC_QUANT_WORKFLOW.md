# Approved Adaptive Agentic Quant Workflow

**Version:** 1.0  
**Status:** APPROVED  
**Date:** 2026-05-03  
**Author:** EdgeSenseAI Architecture Team

---

## Executive Summary

This document defines the approved 24-step Adaptive Agentic Quant Workflow for EdgeSenseAI. This is the canonical reference for all platform components.

**CRITICAL ARCHITECTURAL PRINCIPLES:**

1. **Candidate Universe is DOWNSTREAM, NOT the starting point.** It receives candidates from the Universe Selection / Watchlist Builder step (Step 17).

2. **Models ≠ Agents:**
   - **Models** scan, score, forecast, classify, rank, validate
   - **Agents** coordinate, route, debate, select model stacks, explain, approve workflow tasks

3. **LLMs are gated:** LLMs do NOT scan the whole market. LLMs only run after the LLM Budget Gate (Step 20).

4. **Safety first:**
   - Live trading is **ALWAYS DISABLED** (`live_trading_allowed = false`)
   - Human approval is **ALWAYS REQUIRED** (`human_approval_required = true`)
   - Risk veto **CANNOT BE OVERRIDDEN**
   - Paper/research mode is the **DEFAULT**
   - All LLM calls go through the **LLM Gateway** for tracking and rate limiting

5. **No hardcoded defaults:** The platform does not use AAPL/MSFT/NVDA/AMD as default symbols. All symbols must be explicitly provided or selected by deterministic models.

---

## The 24-Step Workflow

### Phase 1: Market Context & Timing

**Step 1: Market Phase Scheduler**
- Detect current market phase based on US Eastern time
- Phases: `market_closed`, `pre_market`, `market_open_first_30_min`, `market_open`, `midday`, `power_hour`, `after_hours`
- Deterministic rules only - no ML

**Step 2: Timing & Cadence Agent**
- Returns active operational loop based on market phase
- Loops: `research_backtesting_loop`, `pre_market_planning_loop`, `fast_scanning_loop`, `reduced_cadence_pruning_loop`, `power_hour_rotation_loop`, `after_hours_journal_research_loop`

**Step 3: Data Freshness / Quality Gate**
- Verify data source availability and freshness
- Block downstream processing if critical data is stale
- Enforce data quality thresholds

### Phase 2: Market Analysis

**Step 4: Market Regime Model**
- Classify current market regime (trending, ranging, volatile, etc.)
- Determines which strategy types are appropriate
- Deterministic classification based on volatility and trend metrics

**Step 5: Strategy Debate Agent**
- Agents debate which strategies are suitable for current regime
- No LLM - uses deterministic rule-based debate
- Outputs ranked list of viable strategies

**Step 6: Strategy Ranking Model**
- Scores strategies based on:
  - Historical performance in similar regimes
  - Current market fit
  - Risk-adjusted expectancy
  - Account suitability

**Step 7: Model Selection & Meta-Model Agent**
- Selects which models to run based on:
  - Strategy requirements
  - Market phase
  - LLM budget constraints
  - Data availability

### Phase 3: Universe Selection

**Step 8: Universe Selection / Watchlist Builder (THIS IS THE STARTING POINT)**
- **Purpose:** Preselect and rank symbols worth monitoring
- **Input:** Explicit symbols from user OR scan of configured universe
- **Process:**
  1. Data quality gate (must pass first)
  2. Pull snapshot/history from market data
  3. Score components: liquidity, spread, trend, volatility, RVOL, account fit
  4. Weighted combination into universe_score (0-100)
  5. Reject if data unavailable, stale, or score < min_score
- **Output:** Ranked candidates + selected watchlist
- **NO LLMs** - deterministic weighted scoring only
- **NO hardcoded symbols** - only uses explicitly provided symbols

**Step 9: Historical Similarity Search**
- Find historical analogs for candidate symbols
- Match based on technical patterns and regime similarity
- Requires configured historical data pipeline

**Step 10: Trigger Rules + Watchlist TTL**
- Assign trigger conditions to watchlist entries:
  - Price triggers (breakout, pullback to support)
  - Volume triggers (RVOL spike)
  - Time triggers (specific time windows)
- Set time-to-live (TTL) for watchlist entries
- Expired entries automatically removed

### Phase 4: Signal Generation

**Step 11: Cheap Event Scanner Models**
- Lightweight scanners detect:
  - Breakouts/breakdowns
  - Volume spikes
  - Moving average crosses
  - Support/resistance tests
- Runs continuously during active trading phases
- **NO LLMs** - pure technical analysis

**Step 12: Signal Scoring Models**
- Score detected events on:
  - Strength of signal
  - Quality of setup
  - Risk/reward potential
  - Account fit
- Outputs ranked signals with confidence scores

**Step 13: Meta-Model Ensemble Scorer**
- Combines multiple model outputs using:
  - Weighted voting
  - Confidence weighting
  - Historical accuracy weighting
- Produces ensemble score for each candidate

### Phase 5: Validation & Control

**Step 14: LLM Budget Gate**
- **CRITICAL GATE:** All LLM usage passes through here
- Enforces:
  - Daily LLM cost limits (default $10/day)
  - Per-request cost estimation
  - Budget mode: full/conservative/minimal/disabled
- **LLMs do NOT run before this gate**

**Step 15: LangGraph Agent Validation**
- LangGraph-based agent validation flow
- Validates signals through:
  - Context gathering
  - Reasoning chains
  - Consistency checks
- Only runs if LLM Budget Gate allows

**Step 16: Risk / No-Trade / Capital Allocation**
- **VETO AUTHORITY:** Risk check can halt any trade
- Evaluates:
  - Account-level risk (max exposure, drawdown limits)
  - Position-level risk (position size, stop loss)
  - Portfolio heat (correlated exposure)
- **Risk veto CANNOT be overridden**
- `live_trading_allowed` always false
- `human_approval_required` always true

### Phase 6: Downstream Processing

**Step 17: Candidate Universe (DOWNSTREAM STORAGE)**
- **RECEIVES candidates from Universe Selection**
- **NOT the starting point**
- Stores candidates that passed Universe Selection
- Maintains priority scores and metadata
- Persists to Postgres with memory fallback
- Used by Command Center for ranking

**Step 18: Recommendation / Approval / Paper Trade**
- Recommendation Lifecycle service
- Tracks recommendation status:
  - `pending_review`
  - `approved` (human approval required)
  - `rejected`
  - `paper_trade_created`
  - `expired`
- Paper trade outcomes feed into training data
- **No live trading** - paper only

**Step 19: Journal / Drift / Research / Memory**
- Journal entries for all trades and decisions
- Model drift monitoring
- Research notes and hypotheses
- Vector memory for agent context and similarity search

---

## Component Separation: Models vs Agents

### Models (Deterministic, No LLM)

| Model | Purpose | Step |
|-------|---------|------|
| Market Phase Model | Detect market phase | 1 |
| Market Regime Model | Classify regime | 4 |
| Strategy Ranking Model | Score strategies | 6 |
| Universe Selection Model | Rank symbols | 8 |
| Historical Similarity Model | Find analogs | 9 |
| Event Scanner Models | Detect signals | 11 |
| Signal Scoring Models | Score signals | 12 |
| Meta-Model Ensemble | Combine scores | 13 |
| Risk Engine Model | Risk assessment | 16 |
| Paper Trade Outcome Model | PnL calculation | 18 |

### Agents (Coordination, May Use LLM)

| Agent | Purpose | Step |
|-------|---------|------|
| Timing & Cadence Agent | Return cadence plan | 2 |
| Data Quality Agent | Gate data freshness | 3 |
| Strategy Debate Agent | Debate strategy fit | 5 |
| Model Selection Agent | Select model stack | 7 |
| Watchlist TTL Agent | Manage TTL | 10 |
| LLM Budget Gate | Enforce budget | 14 |
| LangGraph Validation Agent | Validate signals | 15 |
| Risk Veto Agent | Risk authority | 16 |
| Recommendation Agent | Manage lifecycle | 18 |
| Journal/Drift Agent | Track outcomes | 19 |

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           MARKET CONTEXT                                 │
│  Market Phase → Cadence Agent → Data Gate → Regime Model                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         STRATEGY SELECTION                               │
│  Strategy Debate → Strategy Rank → Model Selection                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │           UNIVERSE SELECTION / WATCHLIST BUILDER                 │   │
│  │  ─────────────────────────────────────────────────────────────  │   │
│  │  Input: Explicit symbols from user                              │   │
│  │  Process:                                                         │   │
│  │    1. Data quality gate (FIRST)                                 │   │
│  │    2. Pull snapshot/history                                       │   │
│  │    3. Score: liquidity, spread, trend, vol, RVOL, account fit   │   │
│  │    4. Combine into universe_score (0-100)                         │   │
│  │    5. Reject if data unavailable or score < min_score             │   │
│  │  Output: Ranked candidates + selected watchlist                   │   │
│  │  ─────────────────────────────────────────────────────────────  │   │
│  │  NO LLMs. NO hardcoded symbols.                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                    ┌───────────────┼───────────────┐                   │
│                    │               │               │                   │
│                    ▼               ▼               ▼                   │
│         ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│         │ Historical  │  │   Trigger   │  │   Cheap     │             │
│         │  Similarity │  │  Rules+TTL  │  │   Scanner   │             │
│         └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                    │                   │
└────────────────────────────────────────────────────┼───────────────────┘
                                                     │
                                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      SIGNAL PROCESSING                                   │
│  Signal Scoring → Meta-Model Ensemble                                    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      VALIDATION GATES                                    │
│  LLM Budget Gate → LangGraph Agent → Risk Veto (CANNOT OVERRIDE)      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      DOWNSTREAM STORAGE                                  │
│                                                                          │
│  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐     │
│  │ CANDIDATE        │   │ RECOMMENDATION   │   │ PAPER TRADE      │     │
│  │ UNIVERSE         │   │ LIFECYCLE        │   │ OUTCOMES         │     │
│  │ (receives from   │   │ (pending→       │   │ (PnL→training    │     │
│  │  universe sel)   │   │  approved→paper) │   │  data)           │     │
│  └──────────────────┘   └──────────────────┘   └──────────────────┘     │
│                                                                          │
│  ┌──────────────────┐   ┌──────────────────┐                              │
│  │ JOURNAL          │   │ MEMORY/DRIFT     │                              │
│  │ (all decisions)  │   │ (vector search)  │                              │
│  └──────────────────┘   └──────────────────┘                              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Critical Constraints

### LLM Usage Rules

1. **LLMs do NOT scan the whole market**
2. **LLMs only run after Step 14 (LLM Budget Gate)**
3. **LLM Budget Gate enforces:**
   - Daily cost limit (default $10)
   - Per-request cost estimation
   - Budget modes: full/conservative/minimal/disabled
4. **All LLM calls go through LLM Gateway** for tracking

### Trading Safety Rules

1. **`live_trading_allowed = false` (ALWAYS)**
2. **`human_approval_required = true` (ALWAYS)**
3. **Risk veto CANNOT be overridden**
4. **Paper/research mode is DEFAULT**
5. **All recommendations require human approval**

### Data & Symbol Rules

1. **No hardcoded default symbols** (no AAPL/MSFT/NVDA/AMD unless explicitly provided)
2. **Universe Selection uses explicit symbols only**
3. **Scanner uses explicit symbols or latest watchlist only**
4. **Mock data remains explicit-only** (opt-in, never silent fallback)
5. **All data quality gates must pass before downstream processing**

---

## Implementation Phases

### Phase 1: Runtime Timing & Cadence ✅
- Market Phase Scheduler
- Timing & Cadence Agent
- Data Freshness Gate

### Phase 2: Universe Selection & Watchlist Builder 🔄
- Universe Selection service
- Weighted ranker (deterministic, no LLM)
- Watchlist Builder with TTL
- Connection to Candidate Universe (downstream)

### Phase 3: Signal Generation
- Cheap Event Scanner Models
- Signal Scoring Models
- Meta-Model Ensemble

### Phase 4: Validation & Control
- LLM Budget Gate
- LangGraph Agent Validation
- Risk Veto Authority

### Phase 5: Paper Trading & Research
- Recommendation Lifecycle
- Paper Trade Outcomes
- Journal & Memory
- Training Data Generation

---

## Verification Checklist

When implementing components, verify:

- [ ] Candidate Universe is downstream (receives from Universe Selection)
- [ ] Universe Selection uses explicit symbols only
- [ ] No default stock universe hardcoded
- [ ] Scanner uses explicit symbols or latest watchlist only
- [ ] No LLMs used in Universe Selection
- [ ] `live_trading_allowed` is always false
- [ ] `human_approval_required` is always true
- [ ] Risk veto cannot be overridden
- [ ] Mock remains explicit-only (opt-in)
- [ ] All LLM calls go through LLM Gateway
- [ ] LLM Budget Gate enforced before any LLM usage

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-05-03 | EdgeSenseAI Architecture Team | Initial approved architecture |

---

**END OF DOCUMENT**
