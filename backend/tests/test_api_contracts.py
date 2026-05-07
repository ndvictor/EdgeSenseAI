import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_workflow_router_status_contract():
    response = client.get("/api/workflow-router/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["stage"]["stage_number"] == 5
    assert payload["stage"]["stage_key"] == "workflow_router"
    assert payload["data_mode"] == "rules_v1"
    assert payload["updated_at"]
    assert payload["summary"]["router_status"] == "ready"
    assert payload["summary"]["llm_required"] is False
    assert payload["supported_workflows"]
    assert any(c["key"] == "urgency_checker" for c in payload["checkers"])


def test_workflow_router_route_market_open_fast_path_contract():
    response = client.post(
        "/api/workflow-router/route",
        json={
            "session": "market_open",
            "market_condition": {
                "regime": "risk_on",
                "volatility_state": "normal",
                "liquidity_state": "good",
                "data_quality": "pass",
                "urgency": "high",
            },
            "strategy_or_response_status": {
                "proof_status": "proven",
                "paper_status": "passed",
                "requires_backtest": False,
                "already_backtested": True,
            },
            "account_state": {
                "risk_budget_available": True,
                "paper_trading_enabled": True,
                "live_trading_enabled": False,
                "human_approval_required": True,
            },
            "execution_state": {"broker_ready": True, "spread_pass": True, "slippage_pass": True},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    decision = payload["decision"]
    assert decision["stage_number"] == 5
    assert decision["selected_workflow"] == "baseline_fast_path"
    assert decision["workflow_mode"] == "baseline"
    assert decision["llm_used"] is False
    assert decision["decision_id"].startswith("wf_")
    assert decision["created_at"]
    assert "session_checker" in decision["checkers"]
    assert "proof_status_checker" in decision["checkers"]


def test_workflow_router_latest_after_route_run_contract():
    # Ensure at least one decision exists
    _ = client.post(
        "/api/workflow-router/route",
        json={
            "session": "market_open",
            "market_condition": {
                "regime": "risk_on",
                "volatility_state": "normal",
                "liquidity_state": "good",
                "data_quality": "pass",
                "urgency": "high",
            },
            "strategy_or_response_status": {
                "proof_status": "proven",
                "paper_status": "passed",
                "requires_backtest": False,
                "already_backtested": True,
            },
            "account_state": {
                "risk_budget_available": True,
                "paper_trading_enabled": True,
                "live_trading_enabled": False,
                "human_approval_required": True,
            },
            "execution_state": {"broker_ready": True, "spread_pass": True, "slippage_pass": True},
        },
    )
    latest = client.get("/api/workflow-router/latest")
    assert latest.status_code == 200
    payload = latest.json()
    assert payload["status"] == "ok"
    assert payload["decision"]["decision_id"].startswith("wf_")


def test_workflow_router_route_data_quality_fail_contract():
    response = client.post(
        "/api/workflow-router/route",
        json={
            "session": "market_open",
            "market_condition": {
                "regime": "risk_on",
                "volatility_state": "normal",
                "liquidity_state": "good",
                "data_quality": "fail",
                "urgency": "high",
            },
            "strategy_or_response_status": {
                "proof_status": "proven",
                "paper_status": "passed",
                "requires_backtest": False,
                "already_backtested": True,
            },
            "account_state": {
                "risk_budget_available": True,
                "paper_trading_enabled": True,
                "live_trading_enabled": False,
                "human_approval_required": True,
            },
            "execution_state": {"broker_ready": True, "spread_pass": True, "slippage_pass": True},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["decision"]["selected_workflow"] == "no_trade_path"


def test_session_router_status_contract():
    response = client.get("/api/session-router/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["stage"]["stage_number"] == 3
    assert payload["stage"]["stage_key"] == "session_router"
    assert payload["data_mode"] == "rules_v1"
    assert payload["updated_at"]
    assert payload["summary"]["router_status"] == "ready"
    assert payload["summary"]["llm_required"] is False
    assert payload["summary"]["calendar_mode"] == "us_equities_basic"
    assert payload["supported_sessions"]
    assert any(c["key"] == "session_time_checker" for c in payload["checkers"])


def test_session_router_evaluate_market_open_contract():
    response = client.post(
        "/api/session-router/evaluate",
        json={
            "timestamp": "2026-05-07T09:35:00-05:00",
            "timezone": "America/Chicago",
            "market": "us_equities",
            "use_current_time": False,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["session"]["session"] == "market_open"
    assert payload["session"]["is_trading_day"] is True


def test_session_router_evaluate_pre_market_contract():
    response = client.post(
        "/api/session-router/evaluate",
        json={
            "timestamp": "2026-05-07T07:15:00-05:00",
            "timezone": "America/Chicago",
            "market": "us_equities",
            "use_current_time": False,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["session"]["session"] == "pre_market"


def test_session_router_evaluate_weekend_closed_contract():
    response = client.post(
        "/api/session-router/evaluate",
        json={
            "timestamp": "2026-05-09T10:00:00-05:00",
            "timezone": "America/Chicago",
            "market": "us_equities",
            "use_current_time": False,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["session"]["session"] == "closed"
    assert payload["session"]["is_trading_day"] is False


def test_session_router_latest_after_evaluation_contract():
    _ = client.post(
        "/api/session-router/evaluate",
        json={
            "timestamp": "2026-05-07T09:35:00-05:00",
            "timezone": "America/Chicago",
            "market": "us_equities",
            "use_current_time": False,
        },
    )
    latest = client.get("/api/session-router/latest")
    assert latest.status_code == 200
    payload = latest.json()
    assert payload["status"] == "ok"
    assert payload["session"]["session_id"].startswith("sr_")


def test_strategy_eligibility_status_contract():
    response = client.get("/api/strategy-eligibility/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["stage"]["stage_number"] == 7
    assert payload["stage"]["stage_key"] == "strategy_eligibility"
    assert payload["data_mode"] == "rules_v1"
    assert payload["updated_at"]
    assert payload["summary"]["checker_status"] == "ready"
    assert payload["summary"]["llm_required"] is False
    assert payload["supported_strategy_groups"]
    assert any(c["key"] == "proof_status_checker" for c in payload["checkers"])


def test_strategy_eligibility_check_baseline_proven_regime_aware_momentum_contract():
    response = client.post(
        "/api/strategy-eligibility/check",
        json={
            "workflow_context": {"selected_workflow": "baseline_fast_path", "workflow_mode": "baseline", "session": "market_open"},
            "strategy_candidate": {
                "strategy_key": "regime_aware_momentum_catalyst",
                "strategy_group": "regime_aware_momentum",
                "proof_status": "proven",
                "paper_status": "passed",
                "requires_backtest": False,
                "already_backtested": True,
            },
            "market_condition": {
                "regime": "risk_on",
                "volatility_state": "normal",
                "liquidity_state": "good",
                "data_quality": "pass",
                "urgency": "high",
            },
            "features": {
                "rvol_elevated": True,
                "price_above_vwap": True,
                "vwap_reclaiming": False,
                "relative_strength_positive": True,
                "catalyst_confirmed": True,
                "volume_confirms": True,
                "spread_pass": True,
                "risk_reward_pass": True,
            },
            "account_state": {
                "risk_budget_available": True,
                "paper_trading_enabled": True,
                "live_trading_enabled": False,
                "human_approval_required": True,
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    eligibility = payload["eligibility"]
    assert eligibility["eligible"] is True
    assert eligibility["eligibility_status"] == "eligible"
    assert eligibility["strategy_key"] == "regime_aware_momentum_catalyst"
    assert eligibility["strategy_group"] == "regime_aware_momentum"


def test_strategy_eligibility_check_data_quality_fail_blocked_contract():
    response = client.post(
        "/api/strategy-eligibility/check",
        json={
            "workflow_context": {"selected_workflow": "baseline_fast_path", "workflow_mode": "baseline", "session": "market_open"},
            "strategy_candidate": {
                "strategy_key": "regime_aware_momentum_catalyst",
                "strategy_group": "regime_aware_momentum",
                "proof_status": "proven",
                "paper_status": "passed",
                "requires_backtest": False,
                "already_backtested": True,
            },
            "market_condition": {
                "regime": "risk_on",
                "volatility_state": "normal",
                "liquidity_state": "good",
                "data_quality": "fail",
                "urgency": "high",
            },
            "features": {
                "rvol_elevated": True,
                "price_above_vwap": True,
                "vwap_reclaiming": False,
                "relative_strength_positive": True,
                "catalyst_confirmed": True,
                "volume_confirms": True,
                "spread_pass": True,
                "risk_reward_pass": True,
            },
            "account_state": {
                "risk_budget_available": True,
                "paper_trading_enabled": True,
                "live_trading_enabled": False,
                "human_approval_required": True,
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["eligibility"]["eligibility_status"] == "blocked"


def test_strategy_eligibility_check_market_open_unproven_returns_paper_only_contract():
    response = client.post(
        "/api/strategy-eligibility/check",
        json={
            "workflow_context": {"selected_workflow": "baseline_fast_path", "workflow_mode": "baseline", "session": "market_open"},
            "strategy_candidate": {
                "strategy_key": "regime_aware_momentum_catalyst",
                "strategy_group": "regime_aware_momentum",
                "proof_status": "backtest_required",
                "paper_status": "testing",
                "requires_backtest": True,
                "already_backtested": False,
            },
            "market_condition": {
                "regime": "risk_on",
                "volatility_state": "normal",
                "liquidity_state": "good",
                "data_quality": "pass",
                "urgency": "high",
            },
            "features": {
                "rvol_elevated": True,
                "price_above_vwap": True,
                "vwap_reclaiming": False,
                "relative_strength_positive": True,
                "catalyst_confirmed": True,
                "volume_confirms": True,
                "spread_pass": True,
                "risk_reward_pass": True,
            },
            "account_state": {
                "risk_budget_available": True,
                "paper_trading_enabled": True,
                "live_trading_enabled": False,
                "human_approval_required": True,
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["eligibility"]["eligibility_status"] == "paper_only"


def test_strategy_eligibility_latest_after_check_contract():
    _ = client.post(
        "/api/strategy-eligibility/check",
        json={
            "workflow_context": {"selected_workflow": "baseline_fast_path", "workflow_mode": "baseline", "session": "market_open"},
            "strategy_candidate": {
                "strategy_key": "regime_aware_momentum_catalyst",
                "strategy_group": "regime_aware_momentum",
                "proof_status": "proven",
                "paper_status": "passed",
                "requires_backtest": False,
                "already_backtested": True,
            },
            "market_condition": {
                "regime": "risk_on",
                "volatility_state": "normal",
                "liquidity_state": "good",
                "data_quality": "pass",
                "urgency": "high",
            },
            "features": {
                "rvol_elevated": True,
                "price_above_vwap": True,
                "vwap_reclaiming": False,
                "relative_strength_positive": True,
                "catalyst_confirmed": True,
                "volume_confirms": True,
                "spread_pass": True,
                "risk_reward_pass": True,
            },
            "account_state": {
                "risk_budget_available": True,
                "paper_trading_enabled": True,
                "live_trading_enabled": False,
                "human_approval_required": True,
            },
        },
    )
    latest = client.get("/api/strategy-eligibility/latest")
    assert latest.status_code == 200
    payload = latest.json()
    assert payload["status"] == "ok"
    assert payload["eligibility"]["check_id"].startswith("se_")


def _trigger_monitoring_sample_request(
    *,
    asset_class: str = "stock",
    horizon: str = "day_trading",
    eligibility_eligible: bool = True,
    eligibility_status: str = "eligible",
    evaluated_at: str = "2026-05-07T09:35:00-05:00",
    expires_at: str = "2026-05-07T09:45:00-05:00",
    volume_confirms: bool = True,
    price_above_trigger: bool = True,
    price_above_vwap: bool = True,
    spread_pass: bool = True,
    data_quality: str = "pass",
    invalidation_hit: bool = False,
) -> dict:
    return {
        "workflow_context": {"selected_workflow": "baseline_fast_path", "workflow_mode": "baseline", "session": "market_open"},
        "eligibility_context": {
            "eligible": eligibility_eligible,
            "eligibility_status": eligibility_status,
            "strategy_key": "regime_aware_momentum_catalyst",
            "strategy_group": "regime_aware_momentum",
        },
        "trigger_candidate": {
            "symbol": "AMD",
            "asset_class": asset_class,
            "horizon": horizon,
            "trigger_key": "rvol_vwap_breakout_confirm",
            "created_at": "2026-05-07T09:30:00-05:00",
            "expires_at": expires_at,
            "trigger_price": 150.25,
            "current_price": 151.10,
            "vwap": 149.80,
        },
        "current_state": {
            "evaluated_at": evaluated_at,
            "data_quality": data_quality,
            "spread_pass": spread_pass,
            "volume_confirms": volume_confirms,
            "price_above_trigger": price_above_trigger,
            "price_above_vwap": price_above_vwap,
            "invalidation_hit": invalidation_hit,
        },
    }


def test_trigger_monitoring_status_contract():
    response = client.get("/api/trigger-monitoring/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["stage"]["stage_number"] == 8
    assert payload["stage"]["stage_key"] == "trigger_monitoring"
    assert payload["data_mode"] == "rules_v1"
    assert payload["updated_at"]
    assert payload["summary"]["monitor_status"] == "ready"
    assert payload["summary"]["llm_required"] is False
    assert "fired" in payload["supported_trigger_states"]
    assert any(c["key"] == "timing_window_checker" for c in payload["checkers"])


def test_trigger_monitoring_evaluate_fired_contract():
    response = client.post("/api/trigger-monitoring/evaluate", json=_trigger_monitoring_sample_request())
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    ev = payload["trigger_evaluation"]
    assert ev["stage_number"] == 8
    assert ev["evaluation_id"].startswith("tm_")
    assert ev["trigger_state"] == "fired"
    assert ev["llm_used"] is False
    assert ev["timing"]["is_expired"] is False
    assert "execution_planner" in ev["allowed_next_stages"]


def test_trigger_monitoring_evaluate_expired_contract():
    response = client.post(
        "/api/trigger-monitoring/evaluate",
        json=_trigger_monitoring_sample_request(
            evaluated_at="2026-05-07T09:46:00-05:00",
            expires_at="2026-05-07T09:45:00-05:00",
        ),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["trigger_evaluation"]["trigger_state"] == "expired"
    assert payload["trigger_evaluation"]["timing"]["is_expired"] is True


def test_trigger_monitoring_evaluate_asset_scope_blocked_contract():
    response = client.post("/api/trigger-monitoring/evaluate", json=_trigger_monitoring_sample_request(asset_class="crypto"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["trigger_evaluation"]["trigger_state"] == "blocked"
    assert "stocks only" in payload["trigger_evaluation"]["reason"].lower()


def test_trigger_monitoring_evaluate_eligibility_blocked_contract():
    response = client.post(
        "/api/trigger-monitoring/evaluate",
        json=_trigger_monitoring_sample_request(eligibility_eligible=False, eligibility_status="blocked"),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["trigger_evaluation"]["trigger_state"] == "blocked"


def test_trigger_monitoring_latest_after_evaluation_contract():
    _ = client.post("/api/trigger-monitoring/evaluate", json=_trigger_monitoring_sample_request())
    latest = client.get("/api/trigger-monitoring/latest")
    assert latest.status_code == 200
    payload = latest.json()
    assert payload["status"] == "ok"
    assert payload["trigger_evaluation"]["evaluation_id"].startswith("tm_")


def _execution_planner_sample_request(
    *,
    trigger_state: str = "fired",
    asset_class: str = "stock",
    horizon: str = "day_trading",
    spread_percent: float = 0.07,
    execution_enabled: bool = False,
) -> dict:
    return {
        "trigger_evaluation": {
            "trigger_state": trigger_state,
            "symbol": "AMD",
            "asset_class": asset_class,
            "horizon": horizon,
            "trigger_key": "rvol_vwap_breakout_confirm",
        },
        "market_snapshot": {
            "current_price": 151.10,
            "vwap": 149.80,
            "atr": 2.25,
            "bid": 151.05,
            "ask": 151.15,
            "spread_percent": spread_percent,
            "volume_confirms": True,
        },
        "account_state": {
            "account_equity": 10000,
            "cash": 10000,
            "risk_budget_available": True,
            "max_risk_per_trade_percent": 1.0,
            "max_position_size_percent": 20.0,
            "paper_trading_enabled": True,
            "live_trading_enabled": False,
            "human_approval_required": True,
            "execution_enabled": execution_enabled,
        },
        "planning_preferences": {
            "order_style": "limit",
            "stop_method": "atr",
            "target_reward_risk": 2.0,
            "atr_stop_multiplier": 1.0,
            "max_spread_percent": 0.15,
        },
    }


def test_execution_planner_status_contract():
    response = client.get("/api/execution-planner/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["stage"]["stage_number"] == 9
    assert payload["stage"]["stage_key"] == "execution_planner"
    assert payload["data_mode"] == "rules_v1"
    assert payload["updated_at"]
    assert payload["summary"]["planner_status"] == "ready"
    assert payload["summary"]["llm_required"] is False
    assert any(c["key"] == "master_admin_gate" for c in payload["checkers"])


def test_execution_planner_plan_contract_includes_entry_risk_sizing():
    response = client.post("/api/execution-planner/plan", json=_execution_planner_sample_request())
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    plan = payload["execution_plan"]
    assert plan["plan_id"].startswith("ep_")
    assert plan["symbol"] == "AMD"
    assert "entry" in plan and "risk" in plan and "sizing" in plan
    assert plan["llm_used"] is False
    assert plan["risk"]["reward_risk_ratio"] == 2.0


def test_execution_planner_scope_blocked_crypto():
    response = client.post("/api/execution-planner/plan", json=_execution_planner_sample_request(asset_class="crypto"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["execution_plan"]["plan_status"] == "blocked"


def test_execution_planner_trigger_not_fired_blocked():
    response = client.post("/api/execution-planner/plan", json=_execution_planner_sample_request(trigger_state="armed"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["execution_plan"]["plan_status"] == "blocked"
    assert "trigger_not_fired" in payload["execution_plan"]["blockers"]


def test_execution_planner_high_spread_blocked():
    response = client.post("/api/execution-planner/plan", json=_execution_planner_sample_request(spread_percent=0.50))
    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_plan"]["plan_status"] == "blocked"
    assert "spread_too_wide" in payload["execution_plan"]["blockers"]


def test_execution_planner_execution_enabled_false_returns_master_admin_blocker():
    response = client.post("/api/execution-planner/plan", json=_execution_planner_sample_request(execution_enabled=False))
    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_plan"]["plan_status"] == "blocked"
    assert "execution_disabled_by_master_admin" in payload["execution_plan"]["blockers"]


def test_execution_planner_latest_after_planning_contract():
    _ = client.post("/api/execution-planner/plan", json=_execution_planner_sample_request())
    latest = client.get("/api/execution-planner/latest")
    assert latest.status_code == 200
    payload = latest.json()
    assert payload["status"] == "ok"
    assert payload["execution_plan"]["plan_id"].startswith("ep_")


def _execution_plan_for_handoff(
    *,
    plan_status: str = "planned",
    asset_class: str = "stock",
    horizon: str = "day_trading",
    plan_blockers: list[str] | None = None,
) -> dict:
    return {
        "plan_id": "ep_sample",
        "symbol": "AMD",
        "asset_class": asset_class,
        "horizon": horizon,
        "plan_status": plan_status,
        "entry": {"order_type": "limit", "side": "buy", "limit_price": 151.15, "reference_price": 151.10},
        "risk": {
            "stop_loss": 148.85,
            "target_price": 155.60,
            "risk_per_share": 2.25,
            "reward_per_share": 4.50,
            "reward_risk_ratio": 2.0,
            "max_dollar_risk": 100.0,
        },
        "sizing": {
            "planned_quantity": 13,
            "planned_notional": 1964.95,
            "position_size_percent": 19.65,
            "max_allowed_notional": 2000.0,
            "sizing_status": "capped",
        },
        "execution_readiness": {
            "workflow_enabled": True,
            "execution_enabled": False,
            "paper_trading_enabled": True,
            "live_trading_enabled": False,
            "broker_execution_enabled": False,
            "human_approval_required": True,
            "emergency_stop": False,
            "force_close_requested": False,
            "spread_pass": True,
            "slippage_pass": True,
        },
        "blockers": plan_blockers or [],
        "warnings": ["quantity_capped_by_max_position_size"],
    }


def test_execution_planner_precheck_handoff_blocks_when_execution_disabled_and_no_submit():
    response = client.post(
        "/api/execution-planner/precheck-handoff",
        json={
            "execution_plan": _execution_plan_for_handoff(),
            "handoff_preferences": {"org_slug": "default", "source": "execution_planner", "allow_submit": False, "require_human_approval": True},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    handoff = payload["handoff"]
    assert handoff["submitted_order"] is False
    assert handoff["broker_called"] is False
    assert handoff["precheck_status"] == "blocked"
    assert "execution_disabled_by_master_admin" in handoff["blockers"]


def test_execution_planner_precheck_handoff_scope_blocked_crypto():
    response = client.post(
        "/api/execution-planner/precheck-handoff",
        json={"execution_plan": _execution_plan_for_handoff(asset_class="crypto"), "handoff_preferences": {"org_slug": "default"}},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["handoff"]["precheck_status"] == "blocked"
    assert "asset_class_not_supported" in payload["handoff"]["blockers"]


def test_execution_planner_precheck_handoff_blocks_when_plan_has_blockers():
    response = client.post(
        "/api/execution-planner/precheck-handoff",
        json={"execution_plan": _execution_plan_for_handoff(plan_blockers=["spread_too_wide"]), "handoff_preferences": {"org_slug": "default"}},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["handoff"]["precheck_status"] == "blocked"
    assert "plan_contains_blockers" in payload["handoff"]["blockers"]


def test_execution_planner_precheck_handoff_allow_submit_true_still_never_submits():
    response = client.post(
        "/api/execution-planner/precheck-handoff",
        json={
            "execution_plan": _execution_plan_for_handoff(),
            "handoff_preferences": {"org_slug": "default", "allow_submit": True, "source": "execution_planner"},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["handoff"]["submitted_order"] is False
    assert payload["handoff"]["broker_called"] is False


def test_execution_planner_precheck_handoff_plan_status_blocked_returns_blocked():
    response = client.post(
        "/api/execution-planner/precheck-handoff",
        json={"execution_plan": _execution_plan_for_handoff(plan_status="blocked"), "handoff_preferences": {"org_slug": "default"}},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["handoff"]["precheck_status"] == "blocked"
    assert "plan_not_planned" in payload["handoff"]["blockers"]


def test_execution_planner_precheck_handoff_broker_disabled_still_never_calls_broker():
    response = client.post(
        "/api/execution-planner/precheck-handoff",
        json={"execution_plan": _execution_plan_for_handoff(), "handoff_preferences": {"org_slug": "default"}},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["handoff"]["broker_called"] is False


def _position_monitoring_sample_request(
    *,
    asset_class: str = "stock",
    invalidation_hit: bool = False,
    force_close_requested: bool = False,
    emergency_stop: bool = False,
    current_price: float = 152.20,
    entry_price: float = 151.15,
    stop_loss: float = 148.85,
    reduce_at_r_multiple: float = 1.5,
) -> dict:
    return {
        "position": {
            "position_id": "pos_sample",
            "symbol": "AMD",
            "asset_class": asset_class,
            "horizon": "day_trading",
            "side": "long",
            "quantity": 13,
            "entry_price": entry_price,
            "current_price": current_price,
            "stop_loss": stop_loss,
            "target_price": 155.60,
            "opened_at": "2026-05-07T09:40:00-05:00",
        },
        "thesis": {
            "strategy_key": "regime_aware_momentum_catalyst",
            "trigger_key": "rvol_vwap_breakout_confirm",
            "vwap": 149.80,
            "price_above_vwap": True,
            "volume_confirms": True,
            "relative_strength_positive": True,
            "invalidation_hit": invalidation_hit,
        },
        "risk_state": {
            "account_equity": 10000,
            "max_daily_loss_percent": 3.0,
            "current_daily_loss_percent": 0.4,
            "max_position_size_percent": 20.0,
            "force_close_requested": force_close_requested,
            "emergency_stop": emergency_stop,
        },
        "monitoring_preferences": {
            "time_stop_minutes": 45,
            "reduce_at_r_multiple": reduce_at_r_multiple,
            "exit_at_thesis_invalid": True,
        },
        "evaluated_at": "2026-05-07T10:00:00-05:00",
    }


def test_position_monitoring_status_contract():
    response = client.get("/api/position-monitoring/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["stage"]["stage_number"] == 11
    assert payload["stage"]["stage_key"] == "position_monitoring"
    assert payload["data_mode"] == "rules_v1"
    assert payload["updated_at"]
    assert payload["summary"]["monitor_status"] == "ready"
    assert payload["summary"]["llm_required"] is False
    assert "hold" in payload["supported_position_actions"]


def test_position_monitoring_healthy_returns_hold_or_watch():
    response = client.post("/api/position-monitoring/evaluate", json=_position_monitoring_sample_request())
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    ev = payload["position_evaluation"]
    assert ev["evaluation_id"].startswith("pm_")
    assert ev["recommended_action"] in {"hold", "watch"}
    assert ev["llm_used"] is False


def test_position_monitoring_invalidation_hit_returns_exit_review():
    response = client.post("/api/position-monitoring/evaluate", json=_position_monitoring_sample_request(invalidation_hit=True))
    assert response.status_code == 200
    payload = response.json()
    assert payload["position_evaluation"]["recommended_action"] == "exit_review"


def test_position_monitoring_force_close_requested_returns_exit_review():
    response = client.post("/api/position-monitoring/evaluate", json=_position_monitoring_sample_request(force_close_requested=True))
    assert response.status_code == 200
    payload = response.json()
    assert payload["position_evaluation"]["recommended_action"] == "exit_review"


def test_position_monitoring_crypto_asset_class_returns_blocked():
    response = client.post("/api/position-monitoring/evaluate", json=_position_monitoring_sample_request(asset_class="crypto"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["position_evaluation"]["recommended_action"] == "blocked"


def test_position_monitoring_high_r_multiple_returns_reduce():
    # r_multiple ≈ (current-entry)/(entry-stop) -> (154.6-151.15)/2.30 ≈ 1.5
    response = client.post(
        "/api/position-monitoring/evaluate",
        json=_position_monitoring_sample_request(current_price=154.60, reduce_at_r_multiple=1.2),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["position_evaluation"]["recommended_action"] == "reduce"


def test_position_monitoring_latest_after_evaluation_contract():
    _ = client.post("/api/position-monitoring/evaluate", json=_position_monitoring_sample_request())
    latest = client.get("/api/position-monitoring/latest")
    assert latest.status_code == 200
    payload = latest.json()
    assert payload["status"] == "ok"
    assert payload["position_evaluation"]["evaluation_id"].startswith("pm_")


def _patch_market_routes_use_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    """These routes call ``get_market_data_provider()`` with no query override; tests must not depend on workspace runtime_settings.json (e.g. Polygon)."""
    from app.data_providers.mock_provider import MockMarketDataProvider

    import app.main as main_mod

    monkeypatch.setattr(main_mod, "get_market_data_provider", lambda provider=None: MockMarketDataProvider())


def test_health_contract():
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["backend_port"] == 8900
    assert payload["frontend_port"] == 3900
    assert payload["market_data_provider_priority"]


def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "edgesenseai_backend_requests_total" in response.text


def test_lab_inventory_contract():
    response = client.get("/api/lab/inventory")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["data_mode"] == "desired_inventory"
    assert payload["updated_at"]
    summary = payload["summary"]
    assert summary["total_stages"] == 14
    assert summary["total_units"] == 80
    assert summary["present"] + summary["partial"] + summary["missing"] + summary["backlog"] == 80
    assert summary["tested"] == 0
    assert summary["untested"] == 80
    assert summary["ready_to_promote"] == 0
    assert summary["next_action"]

    stages = payload["stages"]
    assert len(stages) == 14
    assert stages[0]["stage_number"] == 1
    assert stages[0]["stage_key"] == "account_owner_configuration"
    assert stages[13]["stage_number"] == 14
    for st in stages:
        assert st["stage_name"]
        su = st["summary"]
        assert su["total_units"] == len(st["units"])
        assert su["present"] + su["partial"] + su["missing"] + su["backlog"] == su["total_units"]

    cats = payload["component_categories"]
    assert len(cats) == 7
    assert {c["category"] for c in cats} == {
        "Python Script",
        "AI-Agent no LLM",
        "AI-Agent + LLM",
        "ML/Statistics Model",
        "State Object",
        "UI Component",
        "Orchestrator",
    }
    for c in cats:
        assert c["total"] == c["present"] + c["partial"] + c["missing"] + c["backlog"]

    unit = next(u for u in payload["stages"][0]["units"] if u["unit_id"] == "unit_001")
    assert unit["name"] == "Account settings schema"
    assert unit["status"] in {
        "present",
        "present_partial",
        "partial",
        "need_to_build",
        "need_to_build_clarify",
        "backlog",
        "unclear",
    }


def test_data_sources_status_contract():
    response = client.get("/api/data-sources/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_sources"] >= 8
    keys = {source["key"] for source in payload["sources"]}
    assert "yfinance" in keys
    assert "alpaca" in keys
    assert "postgresql" in keys
    assert "redis" in keys


def test_data_ingestion_status_contract():
    response = client.get("/api/data-ingestion/status")
    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "ok"
    assert payload["data_mode"] == "summary"
    assert payload["updated_at"]

    summary = payload["summary"]
    assert summary["total_sources"] == 7
    assert summary["active_sources"] >= 0
    assert summary["warning_sources"] >= 0
    assert summary["error_sources"] >= 0
    assert summary["records_ingested_today"] == 0
    assert summary["last_ingested_at"] is None
    assert summary["next_action"]

    sources = payload["sources"]
    keys = {source["key"] for source in sources}
    assert keys == {"alpaca", "polygon", "yfinance", "news", "options_data", "account_state", "paper_trading"}
    for source in sources:
        assert source["name"]
        assert source["provider_type"]
        assert source["status"] in {"ready", "warning", "error", "disabled"}
        assert source["ingestion_mode"] in {"pull", "stream", "webhook", "manual"}
        assert isinstance(source["data_types"], list) and source["data_types"]
        assert source["symbols_tracked"] >= 0
        assert source["records_ingested_today"] == 0
        assert source["last_ingested_at"] is None
        assert source["freshness_seconds"] is None
        assert source["latency_ms"] is None
        assert isinstance(source["errors"], list)
        assert source["next_action"]

    position = payload["pipeline_position"]
    assert position["previous_stage"] == "data_sources"
    assert position["current_stage"] == "data_ingestion"
    assert position["next_stage"] == "data_quality"
    assert position["downstream_stage"] == "feature_store"


def test_normalization_status_contract():
    response = client.get("/api/normalization/status")
    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "ok"
    assert payload["data_mode"] == "summary"
    assert payload["updated_at"]

    summary = payload["summary"]
    assert summary["normalization_status"] in {"ready", "warning", "error", "disabled"}
    assert summary["supported_payloads"] == 5
    assert summary["records_normalized_today"] == 0
    assert summary["warning_count"] == 0
    assert summary["error_count"] == 0
    assert summary["last_normalized_at"] is None
    assert summary["next_action"]

    payload_types = payload["payload_types"]
    assert isinstance(payload_types, list)
    assert {p["key"] for p in payload_types} == {"market_snapshot", "candle", "options_snapshot", "news_event", "macro_snapshot"}

    for p in payload_types:
        assert p["label"]
        assert p["status"] in {"ready", "warning", "error", "disabled"}
        assert p["input_source"] == "market_data_service"
        assert p["output_schema"]
        assert isinstance(p["required_fields"], list) and p["required_fields"]
        assert isinstance(p["optional_fields"], list)
        assert p["downstream_consumers"] == ["data_quality", "feature_store"]
        assert p["records_normalized_today"] == 0
        assert p["last_normalized_at"] is None
        assert isinstance(p["warnings"], list)
        assert isinstance(p["errors"], list)
        assert p["next_action"]

    pos = payload["pipeline_position"]
    assert pos["previous_stage"] == "data_ingestion"
    assert pos["current_stage"] == "normalization"
    assert pos["next_stage"] == "data_quality"
    assert pos["downstream_stage"] == "feature_store"


def test_market_data_snapshot_contract():
    response = client.get("/api/market-data/snapshot/AMD")
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AMD"
    assert "data_quality" in payload
    assert "provider_statuses" in payload or payload["data_quality"] in {"real", "unavailable", "not_configured"}


def test_market_data_history_contract():
    response = client.get("/api/market-data/history/AMD?period=5d&interval=1d")
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AMD"
    assert payload["period"] == "5d"
    assert payload["interval"] == "1d"
    assert "data" in payload


def test_command_center_read_only_contract_without_invented_action():
    response = client.get("/api/command-center")
    assert response.status_code == 200
    payload = response.json()

    top_action = payload["top_action"]
    assert payload["dashboard_mode"] in {
        "no_symbols_selected",
        "candidates_ready_not_ranked",
        "decision_workflow:completed_with_candidates",
        "decision_workflow:completed_no_actionable_candidates",
        "decision_workflow:no_symbols_selected",
    } or payload["dashboard_mode"].startswith("decision_workflow:")

    if top_action is None:
        assert payload["top_recommendations"] == []
        assert "No candidates selected" in payload["cost_usage_message"] or "candidate" in payload["cost_usage_message"].lower()
        return

    assert top_action["symbol"]
    assert top_action["action"] in {"buy", "watch", "avoid"}
    assert 0 <= top_action["confidence"] <= 1
    assert top_action["price_plan"]["current_price"] > 0
    assert top_action["price_plan"]["buy_zone_low"] > 0
    assert top_action["price_plan"]["buy_zone_high"] >= top_action["price_plan"]["buy_zone_low"]
    assert top_action["price_plan"]["stop_loss"] > 0
    assert top_action["price_plan"]["target_price"] > top_action["price_plan"]["current_price"]
    assert top_action["risk_plan"]["reward_risk_ratio"] > 0
    assert top_action["model_votes"]
    assert top_action["invalidation_rules"]
    assert top_action["research_only"] is True
    assert top_action["execution_enabled"] is False


def test_model_status_contract():
    response = client.get("/api/models/status")
    assert response.status_code == 200
    payload = response.json()

    assert payload["data_mode"] == "synthetic_prototype"
    assert payload["live_prediction_enabled"] is False
    assert len(payload["models"]) >= 5
    model_names = {model["name"] for model in payload["models"]}
    assert "ARIMAX Directional Forecast" in model_names
    assert "Kalman Trend Filter" in model_names
    assert "GARCH Volatility Fit" in model_names
    assert "HMM Regime Filter" in model_names
    assert "XGBoost Meta-Ranker" in model_names


def test_live_watchlist_contract():
    response = client.get("/api/live-watchlist/latest")
    assert response.status_code == 200
    payload = response.json()

    assert payload["live_trading_enabled"] is False
    assert payload["execution_enabled"] is False
    assert payload["summary"]["triggered_now"] >= 0
    assert payload["candidates"]


def test_edge_signals_contract():
    response = client.get("/api/edge-signals/latest")
    assert response.status_code == 200
    payload = response.json()

    assert payload["alerts_enabled"] is True
    assert payload["signals"]
    for signal in payload["signals"]:
        assert 0 <= signal["confidence"] <= 1
        assert signal["recommended_action"]
        assert signal["risk_factors"]


def test_candidates_status_contract():
    response = client.get("/api/candidates/status")
    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "ok"
    assert payload["data_mode"] == "summary"
    assert payload["updated_at"]

    summary = payload["summary"]
    assert summary["candidates_status"] in {"ready", "warning", "error", "disabled"}
    assert summary["candidate_sources_configured"] == 7
    assert summary["active_candidates"] >= 0
    assert summary["ranked_candidates"] >= 0
    assert summary["blocked_candidates"] >= 0
    assert summary["last_candidate_at"] is None
    assert summary["next_action"]

    sources = payload["candidate_sources"]
    assert isinstance(sources, list)
    assert {s["key"] for s in sources} == {
        "signal_engine",
        "manual_watchlist",
        "scanner_watchlist",
        "strategy_lab",
        "live_watchlist",
        "market_regime_filter",
        "catalyst_filter",
    }

    for source in sources:
        assert source["label"]
        assert source["status"] in {"ready", "warning", "error", "disabled"}
        assert source["description"]
        assert source["input_stage"] == "signals"
        assert isinstance(source["candidate_types"], list) and source["candidate_types"]
        assert source["downstream_consumers"] == ["recommendations", "risk", "command_center"]
        assert source["active_count"] >= 0
        assert source["ranked_count"] >= 0
        assert source["blocked_count"] >= 0
        assert source["last_candidate_at"] is None
        assert isinstance(source["warnings"], list)
        assert isinstance(source["errors"], list)
        assert source["next_action"]

    pos = payload["pipeline_position"]
    assert pos["previous_stage"] == "signals"
    assert pos["current_stage"] == "candidates"
    assert pos["next_stage"] == "recommendations"
    assert pos["downstream_stage"] == "risk"


def test_market_snapshots_contract(monkeypatch: pytest.MonkeyPatch):
    _patch_market_routes_use_mock(monkeypatch)
    response = client.get("/api/market/snapshots")
    assert response.status_code == 200
    payload = response.json()
    assert payload
    assert payload[0]["current_price"] > 0
    assert payload[0]["data_mode"] == "synthetic_prototype"


def test_features_contract(monkeypatch: pytest.MonkeyPatch):
    _patch_market_routes_use_mock(monkeypatch)
    response = client.get("/api/features/AMD")
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AMD"
    assert 0 <= payload["composite_feature_score"] <= 100
    assert payload["notes"]


def test_model_pipeline_contract(monkeypatch: pytest.MonkeyPatch):
    _patch_market_routes_use_mock(monkeypatch)
    response = client.get("/api/model-pipeline/AMD")
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AMD"
    assert payload["features"]["symbol"] == "AMD"
    assert payload["ranker_score"] >= 0
    assert payload["pipeline_notes"]


def test_model_lab_workflow_contract():
    response = client.post(
        "/api/model-lab/run",
        json={
            "data_source": "mock",
            "model": "xgboost_ranker",
            "symbols": ["AMD", "NVDA", "BTC-USD"],
            "train_split_percent": 70,
            "test_split_percent": 30,
            "feature_set": "prototype_v1",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow_status"] == "completed"
    assert payload["split"]["total_rows"] == 3
    assert payload["split"]["train_rows"] == 2
    assert payload["features"]
    assert payload["ranker_result"]["scores"]
    assert payload["ranker_result"]["rows_scored"] == 3


def test_account_feasibility_contract(monkeypatch: pytest.MonkeyPatch):
    _patch_market_routes_use_mock(monkeypatch)
    response = client.get("/api/account-feasibility/AMD")
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AMD"
    assert payload["max_position_size_dollars"] > 0
    assert payload["max_risk_dollars"] > 0
    assert payload["suggested_expression"]


def test_risk_check_contract(monkeypatch: pytest.MonkeyPatch):
    _patch_market_routes_use_mock(monkeypatch)
    response = client.get("/api/risk-check/AMD")
    assert response.status_code == 200
    payload = response.json()
    assert payload["reward_risk_ratio"] > 0
    assert payload["max_dollar_risk"] > 0
    assert payload["risk_status"] in {"passed", "blocked_or_review"}


def test_market_regime_contract():
    response = client.get("/api/market-regime")
    assert response.status_code == 200
    payload = response.json()
    assert payload["regime_state"]
    assert 0 <= payload["confidence"] <= 1
    assert payload["allowed_strategies"]
    assert payload["blocked_strategies"]
    assert payload["factors"]


def test_backtesting_contract():
    response = client.get("/api/backtesting/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "prototype_contract"
    assert payload["profiles"]
    assert payload["profiles"][0]["metrics"]


def test_journal_contract():
    response = client.get("/api/journal/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "prototype_contract"
    assert payload["total_entries"] >= 1
    assert payload["entries"]
    assert payload["next_steps"]


def test_data_quality_contract():
    response = client.get("/api/data-quality/AMD?asset_class=stock&source=mock")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ticker"] == "AMD"
    assert payload["quality_status"] in {"pass", "warn", "fail"}
    assert payload["data_source"] in {"demo", "placeholder", "source_backed"}
    assert "missing_fields" in payload
    assert "checked_at" in payload


def test_feature_store_run_contract():
    response = client.post(
        "/api/feature-store/run",
        json={"symbol": "AMD", "asset_class": "stock", "horizon": "swing", "source": "mock"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["storage_mode"] == "in_memory"
    assert payload["row"]["ticker"] == "AMD"
    assert payload["row"]["feature_version"] == "foundation_v1"
    assert payload["quality_report"]["quality_status"] in {"pass", "warn", "fail"}


def test_model_runs_registry_and_run_contract():
    registry_response = client.get("/api/model-runs/registry")
    assert registry_response.status_code == 200
    registry = registry_response.json()
    assert registry["available_model_count"] >= 1
    assert registry["placeholder_model_count"] >= 1
    model_keys = {model["key"] for model in registry["models"]}
    assert "weighted_ranker" in model_keys
    assert "finbert_sentiment" in model_keys

    run_response = client.post(
        "/api/model-runs/run",
        json={"symbols": ["AMD"], "asset_class": "stock", "horizon": "swing", "source": "mock"},
    )
    assert run_response.status_code == 200
    run = run_response.json()
    assert run["status"] == "completed"
    assert run["feature_rows"]
    assert run["plan"]["models"]
    assert any(result["model"] == "weighted_ranker" for result in run["results"])
    weighted = next(result for result in run["model_outputs"] if result.get("model_name") == "weighted_ranker_v1")
    assert weighted["status"] == "completed"
    assert 0 <= weighted["prediction_score"] <= 1
    assert 0 <= weighted["probability_score"] <= 1
    assert weighted["pricing"] is None
    assert weighted["feature_contributions"]
    xgboost_outputs = [result for result in run["model_outputs"] if result.get("model") == "xgboost_ranker"]
    assert xgboost_outputs
    assert xgboost_outputs[0]["status"] in {"not_trained", "not_available"}
    assert all(result["status"] != "completed" for result in run["placeholder_models"])


def test_foundation_routes_preserve_existing_agent_endpoints():
    assert client.post("/api/signal-agents/run", json={"symbols": ["AMD"], "agents": ["technical"]}).status_code == 200
    assert client.post("/api/agents/edge-radar/run", json={"symbols": ["AMD"], "data_source": "mock"}).status_code == 200
    summary = client.get("/api/ai-ops/summary")
    assert summary.status_code == 200
    payload = summary.json()
    assert payload["data_quality"]["status"] == "configured"
    assert payload["feature_store"]["status"] == "configured"
    assert payload["model_orchestrator"]["status"] == "configured"


def test_llm_gateway_contracts_and_dry_run_safety(monkeypatch):
    from app.core.settings import settings

    monkeypatch.setattr(settings, "llm_gateway_enable_paid_tests", False)
    assert client.get("/api/llm-gateway/status").status_code == 200
    providers = client.get("/api/llm-gateway/providers")
    assert providers.status_code == 200
    provider_names = {provider["provider"] for provider in providers.json()}
    assert {"openai", "anthropic", "bedrock", "local"}.issubset(provider_names)
    assert client.get("/api/llm-gateway/models").status_code == 200
    assert client.get("/api/llm-gateway/routing-rules").status_code == 200
    assert client.get("/api/llm-gateway/usage").status_code == 200
    costs = client.get("/api/llm-gateway/costs")
    assert costs.status_code == 200
    assert costs.json()["data_source"] == "placeholder"
    assert client.get("/api/llm-gateway/agent-model-map").status_code == 200

    estimate = client.post("/api/llm-gateway/estimate", json={"model": "gpt-4o-mini", "prompt_tokens": 1000, "completion_tokens": 500})
    assert estimate.status_code == 200
    assert estimate.json()["pricing_source"] == "placeholder_estimate"

    test_call = client.post(
        "/api/llm-gateway/test-call",
        json={"provider": "openai", "model": "gpt-4o-mini", "prompt": "safe test", "allow_paid_call": False},
    )
    assert test_call.status_code == 200
    payload = test_call.json()
    assert payload["dry_run"] is True
    assert payload["paid_call_attempted"] is False

    blocked_paid = client.post(
        "/api/llm-gateway/providers/test",
        json={"provider": "openai", "model": "gpt-4o-mini", "prompt": "safe paid gate test", "allow_paid_call": True},
    )
    assert blocked_paid.status_code == 200
    blocked_payload = blocked_paid.json()
    assert blocked_payload["dry_run"] is True
    assert blocked_payload["status"] == "blocked_by_gateway_policy"

    summary = client.get("/api/ai-ops/summary").json()
    assert summary["llm_gateway"]["data_source"] == "placeholder"
    assert "gateway_status" in summary["llm_gateway"]


def test_edge_radar_records_dry_run_llm_usage():
    response = client.post("/api/agents/edge-radar/run", json={"symbols": ["AMD"], "data_source": "mock"})
    assert response.status_code == 200
    usage = client.get("/api/llm-gateway/usage")
    assert usage.status_code == 200
    records = usage.json()
    assert any(record["agent"] in {"Risk Manager Agent", "Portfolio Manager Agent", "Cost Controller Agent"} for record in records)
    assert all(record["dry_run"] is True for record in records if record["agent"] in {"Risk Manager Agent", "Portfolio Manager Agent", "Cost Controller Agent"})


def test_agent_strategy_rules_scanner_and_auto_run_contracts():
    agents = client.get("/api/agents/registry")
    assert agents.status_code == 200
    agent_payload = agents.json()
    assert len(agent_payload) >= 14
    assert any(agent["agent_key"] == "data_quality" for agent in agent_payload)

    strategies = client.get("/api/strategies")
    assert strategies.status_code == 200
    strategy_payload = strategies.json()
    assert len(strategy_payload) >= 9
    assert any(strategy["strategy_key"] == "stock_day_trading" for strategy in strategy_payload)

    strat_summary = client.get("/api/strategies/summary")
    assert strat_summary.status_code == 200
    strat_summary_payload = strat_summary.json()
    assert strat_summary_payload["data_source"] == "strategy_registry"
    assert strat_summary_payload["total_count"] == len(strategy_payload)
    assert strat_summary_payload["total_count"] >= 9

    stock_day = client.get("/api/strategies/stock_day_trading")
    assert stock_day.status_code == 200
    assert stock_day.json()["live_trading_supported"] is False

    rules = client.get("/api/edge-signal-rules")
    assert rules.status_code == 200
    assert any(rule["signal_key"] == "rvol_spike" for rule in rules.json())

    scan = client.post(
        "/api/market-scanner/scan",
        json={"strategy_key": "stock_day_trading", "symbols": ["AMD"], "data_source": "mock", "auto_run": True},
    )
    assert scan.status_code == 200
    scan_payload = scan.json()
    assert scan_payload["strategy_key"] == "stock_day_trading"
    assert scan_payload["recommended_workflow_key"]
    assert scan_payload["safety_state"]["live_trading_enabled"] is False
    assert scan_payload["safety_state"]["require_human_approval"] is True

    auto_status = client.get("/api/auto-run/status")
    assert auto_status.status_code == 200
    assert auto_status.json()["live_trading_enabled"] is False

    updated = client.put("/api/auto-run/status", json={"auto_run_enabled": True, "live_trading_enabled": True})
    assert updated.status_code == 200
    updated_payload = updated.json()
    assert updated_payload["auto_run_enabled"] is True
    assert updated_payload["live_trading_enabled"] is False

    assert client.post("/api/agents/edge-radar/run", json={"symbols": ["AMD"], "data_source": "mock"}).status_code == 200
    assert client.get("/api/llm-gateway/status").status_code == 200
    assert client.get("/api/model-runs/registry").status_code == 200

    summary = client.get("/api/ai-ops/summary")
    assert summary.status_code == 200
    summary_payload = summary.json()
    assert summary_payload["strategy_registry_count"] >= 9
    assert summary_payload["available_agents_count"] >= 1
    assert summary_payload["market_scanner_status"] == "configured"


def test_market_scanner_records_manual_scan_runs():
    response = client.post(
        "/api/market-scanner/scan",
        json={"strategy_key": "stock_day_trading", "symbols": ["AMD"], "data_source": "mock", "auto_run": False},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"]
    assert payload["trigger_type"] == "manual"

    runs = client.get("/api/market-scanner/runs")
    assert runs.status_code == 200
    assert any(run["run_id"] == payload["run_id"] for run in runs.json())

    latest = client.get("/api/market-scanner/runs/latest")
    assert latest.status_code == 200
    assert latest.json()["run_id"] == payload["run_id"]

    by_id = client.get(f"/api/market-scanner/runs/{payload['run_id']}")
    assert by_id.status_code == 200
    assert by_id.json()["strategy_key"] == "stock_day_trading"


def test_scheduled_market_scan_respects_auto_run_controls():
    disabled = client.put("/api/auto-run/status", json={"auto_run_enabled": False})
    assert disabled.status_code == 200
    assert disabled.json()["live_trading_enabled"] is False

    skipped = client.post("/api/market-scanner/run-scheduled-once")
    assert skipped.status_code == 200
    skipped_payload = skipped.json()
    assert skipped_payload["status"] == "skipped"
    assert skipped_payload["scan_run"]["trigger_type"] == "scheduled"

    enabled = client.put("/api/auto-run/status", json={"auto_run_enabled": True, "live_trading_enabled": True})
    assert enabled.status_code == 200
    enabled_payload = enabled.json()
    assert enabled_payload["auto_run_enabled"] is True
    assert enabled_payload["live_trading_enabled"] is False

    scheduled = client.post("/api/market-scanner/run-scheduled-once")
    assert scheduled.status_code == 200
    scheduled_payload = scheduled.json()
    assert scheduled_payload["status"] == "completed"
    assert scheduled_payload["scan"]["trigger_type"] == "scheduled"
    assert scheduled_payload["scan"]["safety_state"]["live_trading_enabled"] is False

    latest = client.get("/api/market-scanner/runs/latest")
    assert latest.status_code == 200
    latest_payload = latest.json()
    assert latest_payload["trigger_type"] == "scheduled"
    assert latest_payload["safety_state"]["live_trading_enabled"] is False

    summary = client.get("/api/ai-ops/summary")
    assert summary.status_code == 200
    summary_payload = summary.json()
    assert summary_payload["latest_market_scan"]
    assert summary_payload["scan_runs_today"] >= 1
    assert summary_payload["last_scheduled_scan_status"] in {"completed", "skipped"}
    assert summary_payload["scanner_status"] == "configured"


def test_strategy_workflow_run_contract_and_scanner_trigger_safety():
    manual = client.post(
        "/api/strategy-workflows/run",
        json={
            "strategy_key": "stock_day_trading",
            "symbol": "AMD",
            "asset_class": "stock",
            "horizon": "day_trade",
            "matched_signal_key": "rvol_spike",
            "trigger_type": "manual",
            "data_source": "mock",
        },
    )
    assert manual.status_code == 200
    manual_payload = manual.json()
    assert manual_payload["workflow_run_id"]
    assert manual_payload["approval_required"] is True
    assert manual_payload["live_trading_allowed"] is False
    assert manual_payload["recommendation"]["paper_only"] is True

    runs = client.get("/api/strategy-workflows/runs")
    assert runs.status_code == 200
    assert any(run["workflow_run_id"] == manual_payload["workflow_run_id"] for run in runs.json())

    latest = client.get("/api/strategy-workflows/runs/latest")
    assert latest.status_code == 200
    assert latest.json()["workflow_run_id"] == manual_payload["workflow_run_id"]

    client.put("/api/auto-run/status", json={"auto_run_enabled": False})
    skipped = client.post("/api/market-scanner/run-scheduled-once")
    assert skipped.status_code == 200
    assert skipped.json()["scan_run"]["workflow_trigger_status"] == "not_triggered"

    scan = client.post(
        "/api/market-scanner/scan",
        json={
            "strategy_key": "stock_day_trading",
            "symbols": ["COOL"],
            "data_source": "mock",
            "auto_run": False,
            "trigger_workflow": True,
        },
    )
    assert scan.status_code == 200
    scan_payload = scan.json()
    assert "workflow_trigger_status" in scan_payload
    assert scan_payload["workflow_trigger_status"] == "triggered"
    assert scan_payload["workflow_run_id"]
    assert scan_payload["safety_state"]["live_trading_enabled"] is False

    duplicate_scan = client.post(
        "/api/market-scanner/scan",
        json={
            "strategy_key": "stock_day_trading",
            "symbols": ["COOL"],
            "data_source": "mock",
            "auto_run": False,
            "trigger_workflow": True,
        },
    )
    assert duplicate_scan.status_code == 200
    duplicate_payload = duplicate_scan.json()
    assert duplicate_payload["workflow_trigger_status"] == "skipped_cooldown_active"
    assert duplicate_payload["workflow_run_id"] is None
    assert duplicate_payload["cooldown_remaining_seconds"] > 0

    client.put("/api/auto-run/status", json={"auto_run_enabled": True})
    scheduled = client.post("/api/market-scanner/run-scheduled-once")
    assert scheduled.status_code == 200
    scheduled_payload = scheduled.json()
    if scheduled_payload.get("scan", {}).get("should_trigger_workflow"):
        assert scheduled_payload["scan"]["workflow_trigger_status"] in {"triggered", "skipped_cooldown_active"}
        if scheduled_payload["scan"]["workflow_trigger_status"] == "triggered":
            assert scheduled_payload["scan"]["workflow_run_id"]
        else:
            assert scheduled_payload["scan"]["cooldown_remaining_seconds"] > 0

    assert client.post("/api/market-scanner/scan", json={"strategy_key": "stock_day_trading", "symbols": ["AMD"], "data_source": "mock"}).status_code == 200
    assert client.post("/api/agents/edge-radar/run", json={"symbols": ["AMD"], "data_source": "mock"}).status_code == 200
    assert client.get("/api/llm-gateway/status").status_code == 200


def test_memory_and_persistence_fallback_contracts():
    from app.services.embedding_service import embed_text

    first = embed_text("AMD momentum workflow memory")
    second = embed_text("AMD momentum workflow memory")
    assert first.embedding == second.embedding
    assert first.provider == "placeholder"

    created = client.post(
        "/api/memory",
        json={
            "memory_type": "workflow_summary",
            "title": "AMD workflow memory",
            "content": "Weighted ranker completed for AMD in paper research mode.",
            "summary": "AMD paper workflow summary",
            "symbol": "AMD",
            "strategy_key": "stock_day_trading",
            "tags": ["test", "workflow"],
        },
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["memory_id"]
    assert payload["embedding_model"] == "placeholder-hash-embedding"

    recent = client.get("/api/memory/recent")
    assert recent.status_code == 200
    assert any(row["memory_id"] == payload["memory_id"] for row in recent.json())

    search = client.post("/api/memory/search", json={"query": "AMD weighted ranker", "symbol": "AMD"})
    assert search.status_code == 200
    search_payload = search.json()
    assert search_payload["data_source"] in {"postgres_pgvector", "postgres_keyword_fallback", "in_memory_fallback"}
    assert search_payload["results"]

    assert client.get(f"/api/memory/{payload['memory_id']}").status_code == 200
    assert client.get("/health").status_code == 200
    summary = client.get("/api/ai-ops/summary")
    assert summary.status_code == 200
    summary_payload = summary.json()
    assert "postgres_persistence_status" in summary_payload
    assert "vector_memory_status" in summary_payload
    assert summary_payload["recent_memory_count"] >= 1


def test_upper_workflow_provider_failure_returns_degraded_response(monkeypatch):
    from app.services import upper_workflow_service

    def fail_freshness(_request):
        raise RuntimeError("yfinance throttled: 429 Too Many Requests")

    monkeypatch.setattr(upper_workflow_service, "run_data_freshness_check", fail_freshness)
    response = client.post(
        "/api/upper-workflow/run",
        json={
            "symbols": ["TSLA", "META", "PLTR"],
            "source": "auto",
            "horizon": "swing",
            "allow_mock": False,
            "build_trigger_rules": True,
            "run_event_scanner": True,
            "run_signal_scoring": True,
            "run_meta_model": True,
            "run_recommendation_pipeline": False,
            "promote_to_candidate_universe": False,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "blocked_by_data_freshness"
    assert payload["blockers"]
    assert any("Data freshness check failed" in blocker for blocker in payload["blockers"])
    assert any("No mock data was used" in warning for warning in payload["warnings"])
    stages = [stage["stage"] for stage in payload["stages"]]
    assert "data_freshness" in stages
    assert "universe_selection" not in stages

    latest = client.get("/api/upper-workflow/latest")
    assert latest.status_code == 200
    assert latest.json()["run_id"] == payload["run_id"]
    history = client.get("/api/upper-workflow/history")
    assert history.status_code == 200
    assert any(run["run_id"] == payload["run_id"] for run in history.json()["runs"])


def test_backtesting_summary_contract():
    r = client.get("/api/backtesting/summary")
    assert r.status_code == 200
    payload = r.json()
    assert payload["mode"] == "prototype_contract"
    assert len(payload["profiles"]) >= 1
    for p in payload["profiles"]:
        assert p["profile_name"]
        assert "promotion_gate" in p


def test_backtesting_action_stubs_not_configured():
    body = {"profile_name": "Small Account Momentum v1"}
    for path in (
        "/api/backtesting/run",
        "/api/backtesting/simulate-execution",
        "/api/backtesting/validate-risk",
        "/api/backtesting/promote-to-paper",
    ):
        resp = client.post(path, json=body)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "not_configured"
        assert (
            "not implemented" in data["message"].lower()
            or "not available" in data["message"].lower()
            or "no historical run" in data["message"].lower()
        )
    sim = client.post("/api/backtesting/simulate-execution", json=body).json()
    assert len(sim["checks"]) == 10
    assert all(c["status"] == "not_configured" for c in sim["checks"])


def test_settings_master_admin_contract():
    response = client.get("/api/settings")
    assert response.status_code == 200
    payload = response.json()
    assert "trading" in payload
    assert "master_admin" in payload

    ma = payload["master_admin"]
    # Required settings fields
    assert "workflow_enabled" in ma
    assert "execution_enabled" in ma
    assert "emergency_stop" in ma
    assert "force_close_requested" in ma
    assert "master_admin_mode" in ma
    assert "last_updated_by" in ma
    assert "updated_at" in ma

    # Required effective gates
    assert "workflow_allowed" in ma
    assert "execution_allowed" in ma
    assert "paper_allowed" in ma
    assert "live_allowed" in ma
    assert "broker_allowed" in ma
    assert "requires_human_approval" in ma
    assert "force_close_pending" in ma
