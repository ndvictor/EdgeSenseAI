# Persistence Gap Audit

Reliability audit for workflow state persistence. This document only marks an object as persisted when code currently writes to or reads from Postgres through the EdgeSenseAI persistence layer.

| Object/state | Currently persisted? | Table name | Read path | Write path | Fallback behavior | Remaining gaps |
| --- | --- | --- | --- | --- | --- | --- |
| candidate_universe | yes | `candidate_universe` | DB-first with memory fallback | DB best-effort plus memory | Uses memory when DB unavailable | None for current candidate registry behavior. |
| decision_workflow_runs | yes | `decision_workflow_runs` | DB-first for latest/list | DB best-effort plus latest memory cache | Command Center GET remains read-only and falls back to latest memory run | None for current workflow run durability. |
| recommendation_lifecycle | yes | `recommendation_lifecycle` | DB-first with memory fallback | DB best-effort plus memory | Uses memory when DB unavailable | None for current lifecycle statuses. |
| paper_trade_outcomes | partial | `paper_trade_outcomes` | DB-backed helper exists | DB helper writes paper outcomes | Helper returns honest DB unavailable result | Audit every paper lifecycle route before calling coverage complete. No live execution. |
| model_training_examples | partial | `model_training_examples` | Table exists | Training examples created from closed paper outcomes where available | No fake labels when source data absent | Needs fuller labeled-outcome pipeline coverage. |
| upper_workflow_runs | yes | `upper_workflow_runs` | DB-first latest/history, memory fallback | Every upper workflow run attempts DB write | `_UPPER_WORKFLOW_HISTORY` remains fallback | Stage-specific payloads are persisted; full original request metadata can be expanded later. |
| trigger_rules | yes | `trigger_rule_runs` | DB-first latest/history, memory fallback | Trigger rule builds attempt DB write | In-memory active rules remain fallback/runtime cache | Active rule state is still runtime memory; build history is durable. |
| event_scanner_runs | yes | `event_scanner_runs` | DB-first latest/list, memory fallback | Event scanner runs attempt DB write | `_SCAN_HISTORY` remains fallback | Duration is reconstructed from timestamps. |
| signal_scoring_runs | yes | `signal_scoring_runs` | DB-first latest/list, memory fallback | Signal scoring runs attempt DB write | `_SCORING_HISTORY` remains fallback | Skipped signal detail can be expanded in a future migration if needed. |
| meta_model_ensemble_runs | yes | `meta_model_ensemble_runs` | DB-first latest/list, memory fallback | Ensemble runs attempt DB write | `_ENSEMBLE_HISTORY` remains fallback | Promoted candidate ids remain in runtime response; table stores ensemble signals and weights. |
| recommendation_pipeline_runs | yes | `recommendation_pipeline_runs` | DB-first latest, memory fallback | Recommendation pipeline runs attempt DB write | Latest memory run remains fallback | List endpoint can be added later if product needs it. |
| journal_outcomes | yes | `journal_outcomes` | DB-first list/get/summary when DB mode is postgres, memory fallback | Journal creation writes memory and attempts DB | Does not fake outcomes; memory summary used when DB unavailable | Existing legacy `journal_entries` remains for generic records; journal outcome source of truth is `journal_outcomes`. |
| performance_drift_runs | yes | `performance_drift_runs` | DB-first latest/history, memory fallback | Drift checks attempt DB write | `_DRIFT_HISTORY` remains fallback | Uses only observed journal/paper evidence; insufficient data remains honest. |
| research_priority_runs | yes | `research_priority_runs` | DB-first latest/history, memory fallback | Research priority runs attempt DB write | `_RESEARCH_HISTORY` remains fallback | Task status updates still mutate latest in-memory object only. |
| model_strategy_update_runs | yes | `model_strategy_update_runs` | DB-first latest/history, memory fallback | Update proposal runs attempt DB write | `_UPDATE_HISTORY` remains fallback | Applying proposals remains explicit and not automated. |
| memory_updates | yes | `memory_update_runs` plus `vector_memories` | DB-first latest/history, memory fallback | Memory update attempts write audit row; vector storage writes separately | No fake `memory_id` when vector storage unavailable | Memory update run audit is durable; vector similarity still falls back honestly if pgvector unavailable. |

## Current Durability Status

- Core required tables: `candidate_universe`, `decision_workflow_runs`, `recommendation_lifecycle`, `paper_trade_outcomes`, `model_training_examples`.
- Workflow durability tables: `upper_workflow_runs`, `trigger_rule_runs`, `event_scanner_runs`, `signal_scoring_runs`, `meta_model_ensemble_runs`, `recommendation_pipeline_runs`, `journal_outcomes`, `performance_drift_runs`, `research_priority_runs`, `model_strategy_update_runs`, `memory_update_runs`.
- Platform readiness should be `partial` if Postgres is connected but workflow durability tables are missing.

## Notes

- Postgres and pgvector availability must be reported honestly through readiness and persistence status checks.
- Provider failures should create degraded/blocked responses with blockers and warnings, not fake market data.
- Live trading remains disabled and human approval remains required across all persisted workflow state.
