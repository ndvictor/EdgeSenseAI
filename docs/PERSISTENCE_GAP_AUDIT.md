# Persistence Gap Audit

Reliability audit for workflow state persistence. This document only marks an object as persisted when code currently writes to or reads from Postgres through the EdgeSenseAI persistence layer.

| Object/state | Currently persisted? | Current storage mode | Table exists? | Required table name | Priority | Next implementation note |
| --- | --- | --- | --- | --- | --- | --- |
| candidate_universe | yes | Postgres with memory fallback | yes | `candidate_universe` | high | Existing service writes and reads candidate entries through persistence helpers. Keep explicit symbol inputs only. |
| decision_workflow_runs | yes | Postgres with latest in-memory cache | yes | `decision_workflow_runs` | high | Decision workflow writes completed and blocked runs. Command Center GET remains read-only and uses latest stored run only. |
| recommendation_lifecycle | yes | Postgres with memory fallback | yes | `recommendation_lifecycle` | high | Lifecycle records persist when DB is available and expose `persistence_mode`. |
| paper_trade_outcomes | partial | Table and persistence helper exist; lifecycle wiring requires verification | yes | `paper_trade_outcomes` | high | Audit paper trading lifecycle write path before claiming full source-of-truth persistence. No live execution. |
| model_training_examples | partial | Table exists; training-example production not fully wired | yes | `model_training_examples` | medium | Wire only from labeled paper outcomes or validated journal outcomes. Do not create fake labels. |
| upper_workflow_runs | no | In-memory history only | no | `upper_workflow_runs` | high | Add a dedicated run table or map safely to a generic workflow run table with full stage trace, blockers, and warnings. |
| trigger_rules | no | In-memory latest/history | no | `trigger_rules` | medium | Persist generated deterministic trigger rules and active-rule snapshots; keep mock/source labels intact. |
| event_scanner_runs | no | In-memory/service response only | no | `event_scanner_runs` | medium | Persist scanner inputs, skipped reasons, matched events, and provider/data-source labels. |
| signal_scoring_runs | no | In-memory latest/history | no | `signal_scoring_runs` | medium | Persist scores, missing inputs, blockers, and model eligibility details. |
| meta_model_ensemble_runs | no | In-memory latest/history | no | `meta_model_ensemble_runs` | medium | Persist ensemble inputs, eligible models, placeholder models, and final rank outputs. |
| recommendation_pipeline_runs | no | In-memory latest only | no | `recommendation_pipeline_runs` | high | Persist paper/research-only recommendation pipeline outputs, approval state, and no-execution safety flags. |
| journal_outcomes | partial | Memory with persistence helper attempted | yes | `journal_entries` | high | Current service stores memory first and attempts DB write, but persistence helper signature should be fully aligned in a follow-up. |
| performance_drift_runs | no | In-memory latest/history | no | `performance_drift_runs` | medium | Persist drift windows, metrics, and detected gaps without fabricating model performance. |
| research_priority_runs | no | In-memory latest/history | no | `research_priority_runs` | low | Persist generated research tasks and evidence references. No paid LLM calls by default. |
| model_strategy_update_runs | no | In-memory latest/history | no | `model_strategy_update_runs` | low | Persist proposed model/strategy updates as reviewable artifacts only. |
| memory_updates | partial | Vector memory store with in-memory fallback; update run history not persisted | yes | `vector_memories` plus future `memory_update_runs` | medium | Vector memories persist when pgvector/Postgres is available. Add explicit memory update run records for audit history. |

## Notes

- Postgres and pgvector availability must be reported honestly through readiness and persistence status checks.
- Provider failures should create degraded/blocked responses with blockers and warnings, not fake market data.
- Live trading remains disabled and human approval remains required across all persisted workflow state.
