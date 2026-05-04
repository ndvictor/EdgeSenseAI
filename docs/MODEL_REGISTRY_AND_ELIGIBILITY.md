# Model Registry and Eligibility Gates

EdgeSenseAI uses a governed model registry so untrained or unevaluated models cannot influence scoring by accident.

## Model groups

- `active_working_models`: models allowed for active research/paper scoring.
- `candidate_open_source_models`: free/open-source research candidates.
- `candidate_pretrained_models`: pretrained research candidates.
- `candidate_statistical_models`: classical statistical research candidates.
- `untrained_internal_models`: internal supervised models without valid artifacts/evaluation/calibration/approval.
- `blocked_models`: models blocked by safety, data, cost, or governance.

## Current production truth

- `weighted_ranker_v1` is the only active working scoring baseline.
- `xgboost_ranker` remains `not_trained` and is not active.
- External/open-source/pretrained/statistical models are research candidates only.
- Candidate models do not influence scoring.
- No model can make a final trade decision.
- Risk gate and human approval remain required.
- No paid model calls are introduced by this registry.

## Why XGBoost is not active yet

`xgboost_ranker` is a future supervised ranker. It cannot be used for active scoring until all requirements are true:

1. `trained_artifact_exists=true`
2. `evaluation_passed=true`
3. `calibration_passed=true`
4. `owner_approved=true`
5. `allowed_for_live_scoring=true`

Until then, it appears as skipped/not trained with a clear blocker and next action.

## Candidate model rules

Candidate models such as Qlib, Chronos, FinBERT, statsmodels, GARCH/EGARCH, HMM, Kalman, River, vectorbt, and backtrader may appear in research and Model Lab visibility, but they must not produce fake prediction outputs or contribute to candidate scores until wrappers and evaluation gates exist.

## Eligibility function

The central check is:

```python
is_model_eligible_for_active_scoring(model_key)
```

The runner and model selection service must call this before selecting or executing a scoring model.

## Promotion path

A model can be promoted only after:

1. Required data exists.
2. Wrapper exists.
3. Backtest or walk-forward evaluation passes.
4. Calibration passes.
5. Safety notes and blockers are resolved.
6. Owner approval is recorded.
7. Risk gate remains required.

## Final decision rule

A model output is evidence only. It is never a final trade decision. Final recommendations still require:

- data quality gate
- risk gate
- no-trade/sit-out gate where applicable
- capital allocation checks
- human approval
- paper/research mode by default

Live trading remains disabled unless a separate execution architecture is explicitly designed and approved.
