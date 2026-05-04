-- Migration: 003_remaining_workflow_state
-- Persists remaining upper workflow and 24-step workflow durability state.

CREATE TABLE IF NOT EXISTS upper_workflow_runs (
    id TEXT PRIMARY KEY,
    run_id TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL,
    horizon TEXT,
    source TEXT,
    symbols_requested JSONB NOT NULL DEFAULT '[]',
    market_phase TEXT,
    active_loop TEXT,
    data_freshness JSONB,
    market_regime JSONB,
    strategy_debate JSONB,
    strategy_ranking JSONB,
    model_selection JSONB,
    universe_selection JSONB,
    trigger_rules JSONB,
    event_scanner JSONB,
    signal_scoring JSONB,
    meta_model_ensemble JSONB,
    recommendation_pipeline JSONB,
    blockers JSONB NOT NULL DEFAULT '[]',
    warnings JSONB NOT NULL DEFAULT '[]',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_upper_workflow_runs_created_at ON upper_workflow_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_upper_workflow_runs_status ON upper_workflow_runs(status);
CREATE INDEX IF NOT EXISTS idx_upper_workflow_runs_run_id ON upper_workflow_runs(run_id);

CREATE TABLE IF NOT EXISTS trigger_rule_runs (
    id TEXT PRIMARY KEY,
    run_id TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL,
    strategy_key TEXT,
    horizon TEXT,
    rules JSONB NOT NULL DEFAULT '[]',
    blockers JSONB NOT NULL DEFAULT '[]',
    warnings JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_trigger_rule_runs_created_at ON trigger_rule_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_trigger_rule_runs_status ON trigger_rule_runs(status);
CREATE INDEX IF NOT EXISTS idx_trigger_rule_runs_strategy_key ON trigger_rule_runs(strategy_key);

CREATE TABLE IF NOT EXISTS event_scanner_runs (
    id TEXT PRIMARY KEY,
    run_id TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL,
    source TEXT,
    horizon TEXT,
    scanned_symbols JSONB NOT NULL DEFAULT '[]',
    matched_events JSONB NOT NULL DEFAULT '[]',
    skipped_symbols JSONB NOT NULL DEFAULT '[]',
    blockers JSONB NOT NULL DEFAULT '[]',
    warnings JSONB NOT NULL DEFAULT '[]',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_event_scanner_runs_created_at ON event_scanner_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_event_scanner_runs_status ON event_scanner_runs(status);

CREATE TABLE IF NOT EXISTS signal_scoring_runs (
    id TEXT PRIMARY KEY,
    run_id TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL,
    horizon TEXT,
    strategy_key TEXT,
    scored_signals JSONB NOT NULL DEFAULT '[]',
    blockers JSONB NOT NULL DEFAULT '[]',
    warnings JSONB NOT NULL DEFAULT '[]',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_signal_scoring_runs_created_at ON signal_scoring_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_signal_scoring_runs_status ON signal_scoring_runs(status);
CREATE INDEX IF NOT EXISTS idx_signal_scoring_runs_strategy_key ON signal_scoring_runs(strategy_key);

CREATE TABLE IF NOT EXISTS meta_model_ensemble_runs (
    id TEXT PRIMARY KEY,
    run_id TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL,
    horizon TEXT,
    strategy_key TEXT,
    ensemble_signals JSONB NOT NULL DEFAULT '[]',
    model_weights_used JSONB NOT NULL DEFAULT '{}',
    blockers JSONB NOT NULL DEFAULT '[]',
    warnings JSONB NOT NULL DEFAULT '[]',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_meta_model_ensemble_runs_created_at ON meta_model_ensemble_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_meta_model_ensemble_runs_status ON meta_model_ensemble_runs(status);
CREATE INDEX IF NOT EXISTS idx_meta_model_ensemble_runs_strategy_key ON meta_model_ensemble_runs(strategy_key);

CREATE TABLE IF NOT EXISTS recommendation_pipeline_runs (
    id TEXT PRIMARY KEY,
    run_id TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL,
    symbol TEXT,
    llm_budget_gate JSONB,
    agent_validation JSONB,
    risk_review JSONB,
    no_trade JSONB,
    capital_allocation JSONB,
    recommendation JSONB,
    blockers JSONB NOT NULL DEFAULT '[]',
    warnings JSONB NOT NULL DEFAULT '[]',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_recommendation_pipeline_runs_created_at ON recommendation_pipeline_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_recommendation_pipeline_runs_status ON recommendation_pipeline_runs(status);
CREATE INDEX IF NOT EXISTS idx_recommendation_pipeline_runs_symbol ON recommendation_pipeline_runs(symbol);

CREATE TABLE IF NOT EXISTS journal_outcomes (
    id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_id TEXT,
    symbol TEXT,
    asset_class TEXT DEFAULT 'stock',
    horizon TEXT DEFAULT 'swing',
    strategy_key TEXT,
    regime TEXT,
    model_stack JSONB NOT NULL DEFAULT '[]',
    expected_outcome TEXT,
    actual_outcome TEXT,
    outcome_label TEXT NOT NULL DEFAULT 'unknown',
    entry_price DOUBLE PRECISION,
    exit_price DOUBLE PRECISION,
    target_price DOUBLE PRECISION,
    stop_loss DOUBLE PRECISION,
    max_favorable_price DOUBLE PRECISION,
    max_adverse_price DOUBLE PRECISION,
    mfe_percent DOUBLE PRECISION,
    mae_percent DOUBLE PRECISION,
    realized_r DOUBLE PRECISION,
    time_to_result_minutes DOUBLE PRECISION,
    followed_plan BOOLEAN,
    confidence_error DOUBLE PRECISION,
    expected_vs_actual TEXT,
    lessons JSONB NOT NULL DEFAULT '[]',
    notes TEXT,
    tags JSONB NOT NULL DEFAULT '[]',
    opened_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_journal_outcomes_created_at ON journal_outcomes(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_journal_outcomes_symbol ON journal_outcomes(symbol);
CREATE INDEX IF NOT EXISTS idx_journal_outcomes_strategy_key ON journal_outcomes(strategy_key);
CREATE INDEX IF NOT EXISTS idx_journal_outcomes_outcome_label ON journal_outcomes(outcome_label);

CREATE TABLE IF NOT EXISTS performance_drift_runs (
    id TEXT PRIMARY KEY,
    run_id TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL,
    sample_count INTEGER DEFAULT 0,
    lookback_days INTEGER,
    strategy_key TEXT,
    model_name TEXT,
    calibration_buckets JSONB NOT NULL DEFAULT '[]',
    false_positive_rate DOUBLE PRECISION,
    win_rate DOUBLE PRECISION,
    average_realized_r DOUBLE PRECISION,
    confidence_error DOUBLE PRECISION,
    affected_models JSONB NOT NULL DEFAULT '[]',
    affected_strategies JSONB NOT NULL DEFAULT '[]',
    recommended_actions JSONB NOT NULL DEFAULT '[]',
    blockers JSONB NOT NULL DEFAULT '[]',
    warnings JSONB NOT NULL DEFAULT '[]',
    checked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_performance_drift_runs_created_at ON performance_drift_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_performance_drift_runs_status ON performance_drift_runs(status);
CREATE INDEX IF NOT EXISTS idx_performance_drift_runs_strategy_key ON performance_drift_runs(strategy_key);

CREATE TABLE IF NOT EXISTS research_priority_runs (
    id TEXT PRIMARY KEY,
    run_id TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL,
    tasks JSONB NOT NULL DEFAULT '[]',
    blockers JSONB NOT NULL DEFAULT '[]',
    warnings JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_research_priority_runs_created_at ON research_priority_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_research_priority_runs_status ON research_priority_runs(status);

CREATE TABLE IF NOT EXISTS model_strategy_update_runs (
    id TEXT PRIMARY KEY,
    run_id TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL,
    strategy_weight_updates JSONB NOT NULL DEFAULT '[]',
    model_weight_updates JSONB NOT NULL DEFAULT '[]',
    paused_strategies JSONB NOT NULL DEFAULT '[]',
    retraining_requests JSONB NOT NULL DEFAULT '[]',
    evaluation_jobs JSONB NOT NULL DEFAULT '[]',
    blockers JSONB NOT NULL DEFAULT '[]',
    warnings JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_model_strategy_update_runs_created_at ON model_strategy_update_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_model_strategy_update_runs_status ON model_strategy_update_runs(status);

CREATE TABLE IF NOT EXISTS memory_update_runs (
    id TEXT PRIMARY KEY,
    run_id TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL,
    source_type TEXT,
    source_id TEXT,
    memory_id TEXT,
    title TEXT,
    metadata JSONB NOT NULL DEFAULT '{}',
    blockers JSONB NOT NULL DEFAULT '[]',
    warnings JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_memory_update_runs_created_at ON memory_update_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_update_runs_status ON memory_update_runs(status);
CREATE INDEX IF NOT EXISTS idx_memory_update_runs_source_type ON memory_update_runs(source_type);

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ DEFAULT NOW()
);
