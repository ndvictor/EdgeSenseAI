from app.services.workflow_orchestrator.state_contract import WorkflowCarryForwardState


def test_to_agent_inputs_always_forces_no_submit_boundaries():
    state = WorkflowCarryForwardState(
        submitted_order=True,
        broker_called=True,
        llm_used=True,
    )

    inputs = state.to_agent_inputs()

    assert inputs["allow_submit"] is False
    assert inputs["submitted_order"] is False
    assert inputs["broker_called"] is False
    assert inputs["llm_used"] is False


def test_workflow_carryforward_state_small_account_defaults():
    state = WorkflowCarryForwardState()

    assert state.asset_class == "stock"
    assert state.horizon == "day_trading"
    assert state.mode == "paper_first"
    assert state.account_equity == 1000.0
    assert state.max_risk_per_trade_percent == 0.5
    assert state.max_daily_loss_percent == 1.5
    assert state.max_open_positions == 1
    assert state.max_trades_per_day == 3
