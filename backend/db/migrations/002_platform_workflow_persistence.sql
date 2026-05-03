-- Migration: 002_platform_workflow_persistence
-- Adds tables for Candidate Universe, Decision Workflow Runs, Recommendation Lifecycle,
-- Paper Trade Outcomes, and Model Training Examples

-- 1. Candidate Universe table
CREATE TABLE IF NOT EXISTS candidate_universe (
    id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    asset_class TEXT NOT NULL DEFAULT 'stock',
    horizon TEXT NOT NULL DEFAULT 'swing',
    source_type TEXT NOT NULL,
    source_detail TEXT,
    priority_score INTEGER NOT NULL DEFAULT 50,
    status TEXT NOT NULL DEFAULT 'active',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_ranked_at TIMESTAMPTZ,
    UNIQUE(symbol, asset_class, horizon, source_type)
);

CREATE INDEX IF NOT EXISTS idx_candidate_universe_status ON candidate_universe(status);
CREATE INDEX IF NOT EXISTS idx_candidate_universe_symbol ON candidate_universe(symbol);

-- 2. Decision Workflow Runs table
CREATE TABLE IF NOT EXISTS decision_workflow_runs (
    id TEXT PRIMARY KEY,
    run_id TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL,
    source TEXT NOT NULL,
    horizon TEXT NOT NULL,
    symbols_requested JSONB NOT NULL DEFAULT '[]',
    candidates JSONB NOT NULL DEFAULT '[]',
    top_action JSONB,
    recommendations JSONB NOT NULL DEFAULT '[]',
    feature_runs JSONB NOT NULL DEFAULT '[]',
    model_runs JSONB NOT NULL DEFAULT '[]',
    blockers JSONB NOT NULL DEFAULT '[]',
    warnings JSONB NOT NULL DEFAULT '[]',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_decision_workflow_runs_created_at ON decision_workflow_runs(created_at DESC);

-- 3. Recommendation Lifecycle table
CREATE TABLE IF NOT EXISTS recommendation_lifecycle (
    id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    asset_class TEXT NOT NULL DEFAULT 'stock',
    horizon TEXT NOT NULL DEFAULT 'swing',
    source TEXT,
    feature_row_id TEXT,
    score INTEGER NOT NULL DEFAULT 0,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
    action_label TEXT,
    status TEXT NOT NULL DEFAULT 'pending_review',
    reason TEXT,
    risk_factors JSONB NOT NULL DEFAULT '[]',
    workflow_run_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_recommendation_lifecycle_status ON recommendation_lifecycle(status);
CREATE INDEX IF NOT EXISTS idx_recommendation_lifecycle_symbol ON recommendation_lifecycle(symbol);
CREATE INDEX IF NOT EXISTS idx_recommendation_lifecycle_created_at ON recommendation_lifecycle(created_at DESC);

-- 4. Paper Trade Outcomes table
CREATE TABLE IF NOT EXISTS paper_trade_outcomes (
    id TEXT PRIMARY KEY,
    recommendation_id TEXT,
    symbol TEXT NOT NULL,
    asset_class TEXT NOT NULL DEFAULT 'stock',
    horizon TEXT NOT NULL DEFAULT 'swing',
    action TEXT,
    entry_price DOUBLE PRECISION,
    exit_price DOUBLE PRECISION,
    stop_loss DOUBLE PRECISION,
    target_price DOUBLE PRECISION,
    quantity DOUBLE PRECISION,
    pnl DOUBLE PRECISION,
    pnl_percent DOUBLE PRECISION,
    outcome_label TEXT,
    opened_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'open',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_paper_trade_outcomes_symbol ON paper_trade_outcomes(symbol);
CREATE INDEX IF NOT EXISTS idx_paper_trade_outcomes_status ON paper_trade_outcomes(status);
CREATE INDEX IF NOT EXISTS idx_paper_trade_outcomes_created_at ON paper_trade_outcomes(created_at DESC);

-- 5. Model Training Examples table
CREATE TABLE IF NOT EXISTS model_training_examples (
    id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    feature_row_id TEXT,
    recommendation_id TEXT,
    paper_trade_outcome_id TEXT,
    features JSONB NOT NULL DEFAULT '{}',
    label JSONB NOT NULL DEFAULT '{}',
    label_type TEXT NOT NULL DEFAULT 'paper_trade_outcome',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_model_training_examples_symbol ON model_training_examples(symbol);
CREATE INDEX IF NOT EXISTS idx_model_training_examples_created_at ON model_training_examples(created_at DESC);

-- Schema migrations tracking table (created here if not exists from 001)
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ DEFAULT NOW()
);
