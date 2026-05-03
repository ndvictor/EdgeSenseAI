# EdgeSenseAI Platform Completion Roadmap

This roadmap captures the remaining work needed to finish EdgeSenseAI as an adaptive agentic quant platform.

The product direction is no longer a simple scanner or dashboard. The target architecture is a closed-loop hedge-fund-style research, scanning, validation, risk, allocation, and learning system.

> Research decides what to test. Models evaluate what works. Agents decide what to run. Scanners wait for triggers. Risk and capital controls decide what is allowed. Journal outcomes improve the next cycle.

---

## 1. Current Platform Foundation

The repository already has these foundations in place:

- Agent Ops Center
- Data Sources view
- Model Lab + Pipeline Control Center
- LLM Gateway and cost-control foundation
- Core Agent Registry
- Strategy Registry
- Edge Signal Rules
- Market Scanner
- Auto-run controls
- Scheduled market scan logging
- Scanner-to-workflow trigger cooldown
- Strategy workflow run foundation
- Feature Store foundation
- Model Orchestrator foundation
- `weighted_ranker_v1` real model runner
- safe `xgboost_ranker` wrapper
- Postgres + pgvector persistence and vector memory foundation
- deterministic placeholder embedding service
- vector memory endpoints

The remaining work should build on these systems, not replace them.

---

## 2. Target Dynamic Workflow

Final desired loop:

```text
Market Phase Scheduler
  ↓
Timing & Cadence Agent
  ↓
Data Freshness / Data Quality Gate
  ↓
Market Regime Model
  ↓
Strategy Debate Agent
  ↓
Strategy Ranking Model
  ↓
Model Selection & Meta-Model Agent
  ↓
Universe / Watchlist Ranking Model
  ↓
Historical Similarity Search
  ↓
Trigger Rules + Watchlist TTL
  ↓
Cheap Event Scanner Models
  ↓
Signal Scoring Models
  ↓
Meta-Model Ensemble Scorer
  ↓
LLM Budget Gate
  ↓
LangGraph Agent Validation
  ↓
Risk Model + Risk Manager Agent
  ↓
No-Trade / Sit-Out Agent
  ↓
Capital Allocation & Trade Plan Agent
  ↓
Recommendation / Approval / Paper Trade
  ↓
Journal + Outcome Labeling
  ↓
Performance Drift + Calibration Model
  ↓
Research Priority Agent
  ↓
Backtest / Model Evaluation / Strategy Weight Update
```

---

## 3. Product Responsibility Map

| Area | Responsibility |
|---|---|
| Agent Ops Center | Workflow, agent, scheduler, registry, persistence, and memory visibility |
| Data Sources | Provider, database, API, LLM, market data, and infrastructure readiness |
| Model Lab | Data quality, feature rows, model planning, model outputs, pretrained models |
| LLM Gateway | Provider routing, cost control, model selection policy, token visibility |
| Edge Signals | Market scanner, daily universe/watchlist, triggers, scan runs |
| Research Lab or Agent Ops section | Research questions, backtest jobs, strategy performance, drift |
| Journal | Decisions, outcomes, labels, review, lessons |
| Settings | Safety controls, auto-run, paper/live mode, approval rules |

Do not create redundant tabs unless the existing page is too overloaded.

---

## 4. Remaining Build Phases

### Phase 1 — Market Phase Scheduler + Timing & Cadence Agent

Goal: make EdgeSenseAI phase-aware.

Tasks:

- [ ] Add market phase service:
  - market closed
  - pre-market
  - market open first 30 minutes
  - midday
  - power hour
  - after-hours
- [ ] Add Timing & Cadence Agent/service.
- [ ] Decide active loop by phase:
  - research loop
  - planning loop
  - scanner loop
  - validation loop
  - journal/learning loop
- [ ] Expose cadence plan endpoint.
- [ ] Add cadence fields to Agent Ops.
- [ ] Add tests for phase detection and loop selection.

Suggested endpoints:

```text
GET /api/timing/market-phase
GET /api/timing/cadence-plan
POST /api/timing/cadence-plan/simulate
```

---

### Phase 2 — Daily Universe Selection + Watchlist Builder

Goal: preselect a focused daily watchlist before live scanning.

Tasks:

- [ ] Add `weighted_universe_ranker_v1`.
- [ ] Add universe selection service.
- [ ] Add daily watchlist persistence.
- [ ] Add watchlist trigger rules.
- [ ] Connect scanner to latest watchlist.
- [ ] Add UI in Edge Signals:
  - Run Universe Selection
  - Latest Watchlist
  - Candidate Ranking
  - Use Latest Watchlist toggle

Suggested endpoints:

```text
POST /api/universe/select
GET /api/universe/runs
GET /api/universe/runs/latest
GET /api/universe/watchlist/latest
GET /api/universe/watchlist/{watchlist_id}
```

Important:

- Do not use OpenAI or Anthropic to scan the whole market.
- Use cheap deterministic code/models first.
- Agents/LLMs only explain, validate, or resolve conflict on top candidates.

---

### Phase 3 — Model Selection & Meta-Model Agent

Goal: dynamically decide which models should scan, score, validate, and rank.

Tasks:

- [ ] Add Model Selection Agent.
- [ ] Add model stack registry by strategy.
- [ ] Add meta-model weighting policy.
- [ ] Add model trust scores by regime.
- [ ] Add model skip reasons:
  - data unavailable
  - stale provider
  - not trained
  - cost too high
  - drift detected
- [ ] Add Meta-Model Ensemble Scorer.
- [ ] Display selected model stack in Model Lab and Agent Ops.

Suggested endpoints:

```text
POST /api/model-selection/plan
GET /api/model-selection/policies
GET /api/model-selection/latest
```

---

### Phase 4 — Data Freshness Gate

Goal: prevent stale/delayed market data from triggering workflows.

Tasks:

- [ ] Add stricter real-time freshness checks:
  - quote age
  - candle age
  - options data age
  - news timestamp
  - provider delay
  - halt status
  - crossed/wide spread sanity
- [ ] Add freshness status to scanner and strategy workflow responses.
- [ ] Block workflow trigger when freshness fails.
- [ ] Add UI badges in Edge Signals and Data Sources.

Suggested endpoint:

```text
GET /api/data-quality/freshness/{symbol}
```

---

### Phase 5 — LLM Budget Gate

Goal: decide if a candidate is worth spending LLM tokens on.

Tasks:

- [ ] Add LLM Budget Gate service.
- [ ] Check:
  - score threshold
  - risk eligibility
  - remaining daily budget
  - task type
  - model tier
- [ ] Route low-value candidates to deterministic-only output.
- [ ] Allow strong reasoning only for high-quality or complex candidates.
- [ ] Add LLM budget gate visibility in LLM Gateway and Agent Ops.

Suggested endpoint:

```text
POST /api/llm-gateway/budget-gate/evaluate
```

---

### Phase 6 — No-Trade / Sit-Out Agent

Goal: make no-trade a first-class decision.

Tasks:

- [ ] Add No-Trade Agent/service.
- [ ] Trigger when:
  - regime unclear
  - model drift high
  - data stale
  - spreads poor
  - too many false triggers
  - buying power too low
  - daily risk/cost budget reached
- [ ] Add output:
  - no_trade_reason
  - watch_only
  - reduce_cadence
  - preserve_capital
- [ ] Add UI display in recommendations and Agent Ops.

Suggested endpoint:

```text
POST /api/no-trade/evaluate
```

---

### Phase 7 — Capital Allocation & Trade Plan Agent

Goal: convert validated candidates into structured plans.

Tasks:

- [ ] Add capital allocation service.
- [ ] Add trade plan service.
- [ ] Add Capital Allocation & Trade Plan Agent.
- [ ] Calculate:
  - opportunity score
  - capital allocation
  - risk dollars
  - position size
  - entry zone
  - invalidation level
  - target zone
  - timeout rule
  - rotation rule
- [ ] Ensure price levels are deterministic, not hallucinated by LLMs.
- [ ] Risk Manager veto cannot be overridden.
- [ ] No live execution.

Suggested endpoints:

```text
POST /api/capital-allocation/plan
GET /api/capital-allocation/plans
GET /api/capital-allocation/plans/latest
```

---

### Phase 8 — Research & Backtest Planning Layer

Goal: make research and backtesting agent-directed.

Tasks:

- [ ] Add Research Question Agent.
- [ ] Add Backtest Selection Agent.
- [ ] Add Model Evaluation Agent.
- [ ] Add research/backtest job records:
  - research questions
  - backtest jobs
  - backtest results
  - model evaluations
  - strategy performance records
- [ ] Generate backtest plans based on:
  - journal outcomes
  - false positives
  - missed triggers
  - model confidence errors
  - risk rejects
  - strategy drift
- [ ] Use vector memory to retrieve similar past setups.
- [ ] Add compact UI in Agent Ops or a future Research section.

Suggested endpoints:

```text
GET /api/research/questions
POST /api/research/questions/generate
GET /api/research/backtest-jobs
POST /api/research/backtest-jobs/plan
GET /api/research/backtest-jobs/{job_id}
POST /api/research/backtest-jobs/{job_id}/run-placeholder
GET /api/research/model-evaluations
POST /api/research/model-evaluations/evaluate
GET /api/research/strategy-performance
```

---

### Phase 9 — External / Pretrained Model Registry

Goal: incorporate external financial/time-series/sentiment models safely.

Tasks:

- [ ] Add external/pretrained model registry.
- [ ] Register:
  - Qlib
  - Chronos / Chronos-Bolt
  - TimeGPT
  - FinBERT
  - statsmodels ARIMAX/VAR
  - GARCH/EGARCH
  - HMM/Markov switching
  - River online models
  - vectorbt/backtrader research engines
- [ ] Add safe wrappers:
  - no paid calls by default
  - no fake predictions
  - clear status: available, package_missing, requires_api_key, not_configured
- [ ] Route outputs as features, not autonomous trade decisions.
- [ ] Add Model Lab visibility.

Suggested endpoint:

```text
GET /api/model-runs/external-registry
```

---

### Phase 10 — Calibration + Drift Monitoring

Goal: measure whether confidence and model outputs are reliable.

Tasks:

- [ ] Add calibration service.
- [ ] Track score bucket performance:
  - 50-60
  - 60-70
  - 70-80
  - 80-90
  - 90+
- [ ] Track actual follow-through rate.
- [ ] Track model overconfidence.
- [ ] Track strategy drift by regime/time of day.
- [ ] Feed results into Model Selection Agent.

Suggested endpoints:

```text
GET /api/performance/calibration
GET /api/performance/drift
POST /api/performance/drift/evaluate
```

---

### Phase 11 — Journal Outcome Labeling

Goal: convert recommendations and paper trades into labeled training data.

Tasks:

- [ ] Add outcome labeling service.
- [ ] Track:
  - max favorable excursion
  - max adverse excursion
  - time-to-result
  - signal follow-through
  - R multiple proxy
  - spread/slippage proxy
  - trigger quality
  - risk reject correctness
- [ ] Store labels in Postgres and vector memory.
- [ ] Feed labels into future XGBoost/meta-labeling training.

Suggested endpoints:

```text
POST /api/journal/label-outcome
GET /api/journal/outcome-labels
```

---

### Phase 12 — Approval Queue + Paper Trade Lifecycle Completion

Goal: make the output operational while still safe.

Tasks:

- [ ] Add approval request records.
- [ ] Add approval queue UI.
- [ ] Add approve/reject endpoints.
- [ ] On approval, create paper trade only.
- [ ] No live trading until explicitly designed later.
- [ ] Journal approval decision and paper outcome.

Suggested endpoints:

```text
GET /api/approvals
POST /api/approvals/{approval_id}/approve
POST /api/approvals/{approval_id}/reject
```

---

## 5. Safety Rules That Must Stay True

- [ ] Live trading disabled by default.
- [ ] Paper trading allowed.
- [ ] Human approval required.
- [ ] No paid LLM calls by default.
- [ ] Agents do not bypass LLM Gateway.
- [ ] Scanner does not use LLMs across the whole market.
- [ ] Risk Manager veto cannot be overridden by Portfolio or Capital Agent.
- [ ] No external/pretrained model is allowed to make final trade decisions.
- [ ] No recommendation should be treated as financial advice.

---

## 6. Recommended Build Order

1. Market Phase Scheduler + Timing & Cadence Agent
2. Daily Universe Selection + Watchlist Builder
3. Model Selection & Meta-Model Agent
4. Data Freshness Gate
5. LLM Budget Gate
6. No-Trade / Sit-Out Agent
7. Capital Allocation & Trade Plan Agent
8. Research & Backtest Planning Layer
9. External / Pretrained Model Registry
10. Calibration + Drift Monitoring
11. Journal Outcome Labeling
12. Approval Queue + Paper Trade Lifecycle

---

## 7. Validation Standard For Every Phase

Each phase must include:

```text
cd backend && python -m compileall app
cd backend && PYTHONPATH=. pytest -q
cd frontend && npm run build
```

Every final task report must include:

- files created
- files modified
- files deleted
- endpoints added/changed
- safety guarantees
- existing endpoints preserved
- validation results
- git status --short
- git diff --stat
- git diff --name-only

---

## 8. Definition Of Done

EdgeSenseAI is platform-complete when it can:

1. Identify market phase.
2. Choose active loop and cadence.
3. Evaluate data quality and freshness.
4. Classify market regime.
5. Debate/rank strategies.
6. Select model stack dynamically.
7. Build daily watchlist.
8. Monitor triggers cheaply.
9. Score triggered candidates with models.
10. Validate only qualified candidates with agents.
11. Gate LLM spend.
12. Apply risk veto.
13. Choose no-trade when appropriate.
14. Build capital allocation and trade plan.
15. Create approval-gated recommendation.
16. Paper trade only after approval.
17. Journal outcomes.
18. Label outcomes.
19. Detect drift and calibration issues.
20. Generate research/backtest jobs.
21. Update model/strategy weights.
22. Store/retrieve memory in Postgres + pgvector.

This is the closed loop required for an adaptive agentic quant workflow.
