-- EdgeSenseAI Research / Backtest Promotion Workflow tables
-- Safe to run manually in Supabase/Postgres. The application also registers
-- equivalent SQLAlchemy models through Base.metadata.create_all.

CREATE TABLE IF NOT EXISTS model_artifacts (
    id TEXT PRIMARY KEY,
    model_key TEXT NOT NULL,
    artifact_version TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    artifact_uri TEXT NULL,
    artifact_hash TEXT NULL,
    provider TEXT NULL,
    source TEXT NOT NULL DEFAULT 'manual',
    status TEXT NOT NULL DEFAULT 'missing',
    trained_on_start_date TIMESTAMPTZ NULL,
    trained_on_end_date TIMESTAMPTZ NULL,
    feature_version TEXT NULL,
    label_definition TEXT NULL,
    created_by TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (model_key, artifact_version)
);
CREATE INDEX IF NOT EXISTS idx_model_artifacts_model_key ON model_artifacts(model_key);
CREATE INDEX IF NOT EXISTS idx_model_artifacts_model_version ON model_artifacts(model_key, artifact_version);
CREATE INDEX IF NOT EXISTS idx_model_artifacts_status ON model_artifacts(status);
CREATE INDEX IF NOT EXISTS idx_model_artifacts_created_at ON model_artifacts(created_at);

CREATE TABLE IF NOT EXISTS model_evaluation_runs (
    id TEXT PRIMARY KEY,
    model_key TEXT NOT NULL,
    artifact_id TEXT NULL REFERENCES model_artifacts(id),
    evaluation_type TEXT NOT NULL,
    dataset_source TEXT NOT NULL,
    dataset_start_date TIMESTAMPTZ NULL,
    dataset_end_date TIMESTAMPTZ NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    passed BOOLEAN NOT NULL DEFAULT false,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    minimum_requirements JSONB NOT NULL DEFAULT '{}'::jsonb,
    failure_reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_by TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_model_eval_model_key ON model_evaluation_runs(model_key);
CREATE INDEX IF NOT EXISTS idx_model_eval_artifact_id ON model_evaluation_runs(artifact_id);
CREATE INDEX IF NOT EXISTS idx_model_eval_status ON model_evaluation_runs(status);
CREATE INDEX IF NOT EXISTS idx_model_eval_passed ON model_evaluation_runs(passed);
CREATE INDEX IF NOT EXISTS idx_model_eval_created_at ON model_evaluation_runs(created_at);

CREATE TABLE IF NOT EXISTS model_calibration_runs (
    id TEXT PRIMARY KEY,
    model_key TEXT NOT NULL,
    artifact_id TEXT NULL REFERENCES model_artifacts(id),
    calibration_type TEXT NOT NULL,
    dataset_source TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    passed BOOLEAN NOT NULL DEFAULT false,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    calibration_report JSONB NOT NULL DEFAULT '{}'::jsonb,
    failure_reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_by TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_model_calib_model_key ON model_calibration_runs(model_key);
CREATE INDEX IF NOT EXISTS idx_model_calib_artifact_id ON model_calibration_runs(artifact_id);
CREATE INDEX IF NOT EXISTS idx_model_calib_status ON model_calibration_runs(status);
CREATE INDEX IF NOT EXISTS idx_model_calib_passed ON model_calibration_runs(passed);
CREATE INDEX IF NOT EXISTS idx_model_calib_created_at ON model_calibration_runs(created_at);

CREATE TABLE IF NOT EXISTS model_promotion_reviews (
    id TEXT PRIMARY KEY,
    model_key TEXT NOT NULL,
    artifact_id TEXT NULL REFERENCES model_artifacts(id),
    evaluation_run_id TEXT NULL REFERENCES model_evaluation_runs(id),
    calibration_run_id TEXT NULL REFERENCES model_calibration_runs(id),
    requested_status TEXT NOT NULL,
    decision TEXT NOT NULL DEFAULT 'pending',
    owner_approved BOOLEAN NOT NULL DEFAULT false,
    reviewed_by TEXT NULL,
    review_notes TEXT NULL,
    risk_gate_required BOOLEAN NOT NULL DEFAULT true,
    human_approval_required BOOLEAN NOT NULL DEFAULT true,
    final_trade_decision_allowed BOOLEAN NOT NULL DEFAULT false,
    live_scoring_allowed BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    reviewed_at TIMESTAMPTZ NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_model_promo_model_key ON model_promotion_reviews(model_key);
CREATE INDEX IF NOT EXISTS idx_model_promo_decision ON model_promotion_reviews(decision);
CREATE INDEX IF NOT EXISTS idx_model_promo_owner_approved ON model_promotion_reviews(owner_approved);
CREATE INDEX IF NOT EXISTS idx_model_promo_created_at ON model_promotion_reviews(created_at);

CREATE TABLE IF NOT EXISTS strategy_backtest_runs (
    id TEXT PRIMARY KEY,
    strategy_key TEXT NOT NULL,
    run_type TEXT NOT NULL,
    dataset_source TEXT NOT NULL,
    dataset_start_date TIMESTAMPTZ NULL,
    dataset_end_date TIMESTAMPTZ NULL,
    symbols JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'pending',
    passed BOOLEAN NOT NULL DEFAULT false,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    assumptions JSONB NOT NULL DEFAULT '{}'::jsonb,
    failure_reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_by TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_strategy_bt_strategy_key ON strategy_backtest_runs(strategy_key);
CREATE INDEX IF NOT EXISTS idx_strategy_bt_status ON strategy_backtest_runs(status);
CREATE INDEX IF NOT EXISTS idx_strategy_bt_passed ON strategy_backtest_runs(passed);
CREATE INDEX IF NOT EXISTS idx_strategy_bt_created_at ON strategy_backtest_runs(created_at);

CREATE TABLE IF NOT EXISTS model_backtest_runs (
    id TEXT PRIMARY KEY,
    model_key TEXT NOT NULL,
    artifact_id TEXT NULL REFERENCES model_artifacts(id),
    run_type TEXT NOT NULL,
    dataset_source TEXT NOT NULL,
    dataset_start_date TIMESTAMPTZ NULL,
    dataset_end_date TIMESTAMPTZ NULL,
    symbols JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'pending',
    passed BOOLEAN NOT NULL DEFAULT false,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    assumptions JSONB NOT NULL DEFAULT '{}'::jsonb,
    failure_reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_by TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_model_bt_model_key ON model_backtest_runs(model_key);
CREATE INDEX IF NOT EXISTS idx_model_bt_artifact_id ON model_backtest_runs(artifact_id);
CREATE INDEX IF NOT EXISTS idx_model_bt_status ON model_backtest_runs(status);
CREATE INDEX IF NOT EXISTS idx_model_bt_passed ON model_backtest_runs(passed);
CREATE INDEX IF NOT EXISTS idx_model_bt_created_at ON model_backtest_runs(created_at);

CREATE TABLE IF NOT EXISTS research_experiment_runs (
    id TEXT PRIMARY KEY,
    experiment_key TEXT NOT NULL,
    experiment_type TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_key TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 50,
    status TEXT NOT NULL DEFAULT 'queued',
    objective TEXT NOT NULL,
    input_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    blockers JSONB NOT NULL DEFAULT '[]'::jsonb,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_by TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_research_exp_key ON research_experiment_runs(experiment_key);
CREATE INDEX IF NOT EXISTS idx_research_exp_type ON research_experiment_runs(experiment_type);
CREATE INDEX IF NOT EXISTS idx_research_target ON research_experiment_runs(target_type, target_key);
CREATE INDEX IF NOT EXISTS idx_research_status ON research_experiment_runs(status);
CREATE INDEX IF NOT EXISTS idx_research_priority ON research_experiment_runs(priority);
CREATE INDEX IF NOT EXISTS idx_research_created_at ON research_experiment_runs(created_at);
