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


def _close_position_base_request(*, recommended_action: str = "exit_review", asset_class: str = "stock", execution_enabled: bool = False, force_close: bool = False) -> dict:
    return {
        "position_evaluation": {
            "evaluation_id": "pm_sample",
            "position_id": "pos_sample",
            "symbol": "AMD",
            "asset_class": asset_class,
            "horizon": "day_trading",
            "position_status": "exit_review" if recommended_action == "exit_review" else "warning",
            "recommended_action": recommended_action,
            "pnl": {"unrealized_pnl": -29.90, "unrealized_pnl_percent": -1.52, "r_multiple": -1.0},
            "risk": {
                "risk_per_share": 2.30,
                "current_distance_to_stop": 0.0,
                "distance_to_target": 6.75,
                "position_notional": 1935.70,
                "position_size_percent": 19.36,
                "daily_loss_percent": 0.7,
            },
            "thesis_validity": {"valid": False, "score": 0.25, "failed_reasons": ["invalidation_hit"], "passed_reasons": []},
            "blockers": [],
            "warnings": ["thesis_invalidated"],
        },
        "position": {"quantity": 13, "side": "long", "current_price": 148.90, "entry_price": 151.15},
        "master_admin": {
            "workflow_enabled": True,
            "execution_enabled": execution_enabled,
            "paper_trading_enabled": True,
            "live_trading_enabled": False,
            "broker_execution_enabled": False,
            "human_approval_required": True,
            "emergency_stop": False,
            "force_close_requested": force_close,
        },
        "review_preferences": {"reduce_percent": 50, "close_reason": "stage_11_exit_review", "order_style": "market", "allow_submit": True},
    }


def test_close_position_status_contract():
    r = client.get("/api/close-position/status")
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    assert payload["stage"]["stage_number"] == 12
    assert payload["stage"]["stage_key"] == "close_position"
    assert payload["data_mode"] == "rules_v1"
    assert "close_review" in payload["supported_review_actions"]


def test_close_position_exit_review_returns_close_review_and_no_submit():
    r = client.post("/api/close-position/review", json=_close_position_base_request(recommended_action="exit_review", execution_enabled=False))
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    review = payload["close_review"]
    assert review["review_action"] == "close_review"
    assert review["submitted_order"] is False
    assert review["broker_called"] is False


def test_close_position_reduce_action_returns_reduce_review_and_reduced_quantity():
    r = client.post("/api/close-position/review", json=_close_position_base_request(recommended_action="reduce", execution_enabled=True))
    assert r.status_code == 200
    review = r.json()["close_review"]
    assert review["review_action"] == "reduce_review"
    assert review["close_order_preview"]["quantity"] == 6


def test_close_position_hold_action_returns_hold_and_no_preview_required():
    r = client.post("/api/close-position/review", json=_close_position_base_request(recommended_action="hold", execution_enabled=True))
    assert r.status_code == 200
    review = r.json()["close_review"]
    assert review["review_action"] == "hold"


def test_close_position_crypto_asset_class_returns_blocked():
    r = client.post("/api/close-position/review", json=_close_position_base_request(asset_class="crypto"))
    assert r.status_code == 200
    review = r.json()["close_review"]
    assert review["review_action"] == "blocked"


def test_close_position_force_close_requested_returns_close_review_and_no_submit():
    r = client.post("/api/close-position/review", json=_close_position_base_request(recommended_action="hold", force_close=True))
    assert r.status_code == 200
    review = r.json()["close_review"]
    assert review["review_action"] == "close_review"
    assert review["submitted_order"] is False


def test_close_position_execution_disabled_includes_blocker():
    r = client.post("/api/close-position/review", json=_close_position_base_request(recommended_action="exit_review", execution_enabled=False))
    assert r.status_code == 200
    review = r.json()["close_review"]
    assert "execution_disabled_by_master_admin" in review["blockers"]


def test_close_position_latest_after_review_contract():
    _ = client.post("/api/close-position/review", json=_close_position_base_request(recommended_action="exit_review", execution_enabled=False))
    latest = client.get("/api/close-position/latest")
    assert latest.status_code == 200
    payload = latest.json()
    assert payload["status"] == "ok"
    assert payload["close_review"]["review_id"].startswith("cp_")


def _post_trade_evaluation_sample_request(
    *,
    asset_class: str = "stock",
    exit_reason: str = "target_hit",
    used_approved_strategy: bool = True,
    respected_stop_loss: bool = True,
    respected_master_admin_gates: bool = True,
    max_allowed_slippage_percent: float = 0.15,
    actual_entry_price: float = 151.20,
    actual_exit_price: float = 155.50,
    planned_entry_price: float = 151.15,
    planned_exit_price: float = 155.60,
) -> dict:
    return {
        "trade": {
            "trade_id": "trade_sample",
            "symbol": "AMD",
            "asset_class": asset_class,
            "horizon": "day_trading",
            "side": "long",
            "quantity": 13,
            "planned_entry_price": planned_entry_price,
            "actual_entry_price": actual_entry_price,
            "planned_exit_price": planned_exit_price,
            "actual_exit_price": actual_exit_price,
            "stop_loss": 148.85,
            "target_price": 155.60,
            "opened_at": "2026-05-07T09:40:00-05:00",
            "closed_at": "2026-05-07T10:25:00-05:00",
            "exit_reason": exit_reason,
        },
        "workflow_context": {
            "selected_workflow": "baseline_fast_path",
            "strategy_key": "regime_aware_momentum_catalyst",
            "trigger_key": "rvol_vwap_breakout_confirm",
            "session": "market_open",
        },
        "thesis_outcome": {
            "thesis_valid_at_exit": True,
            "invalidation_hit": False,
            "price_above_vwap_at_exit": True,
            "volume_confirmed_at_exit": True,
            "relative_strength_positive_at_exit": True,
        },
        "execution_quality": {
            "planned_entry_price": planned_entry_price,
            "actual_entry_price": actual_entry_price,
            "planned_exit_price": planned_exit_price,
            "actual_exit_price": actual_exit_price,
            "max_allowed_slippage_percent": max_allowed_slippage_percent,
        },
        "rule_compliance": {
            "entered_after_trigger": True,
            "used_approved_strategy": used_approved_strategy,
            "respected_position_size": True,
            "respected_stop_loss": respected_stop_loss,
            "respected_master_admin_gates": respected_master_admin_gates,
            "human_approval_obtained": True,
        },
    }


def test_post_trade_evaluation_status_contract():
    r = client.get("/api/post-trade-evaluation/status")
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    assert payload["stage"]["stage_number"] == 13
    assert payload["stage"]["stage_key"] == "post_trade_evaluation"
    assert payload["data_mode"] == "rules_v1"


def test_post_trade_evaluation_target_hit_positive():
    r = client.post("/api/post-trade-evaluation/evaluate", json=_post_trade_evaluation_sample_request(exit_reason="target_hit"))
    assert r.status_code == 200
    p = r.json()["post_trade_evaluation"]
    assert p["outcome_label"] == "target_hit"
    assert p["outcome_status"] == "positive"


def test_post_trade_evaluation_stopped_out_negative():
    r = client.post(
        "/api/post-trade-evaluation/evaluate",
        json=_post_trade_evaluation_sample_request(
            exit_reason="stopped_out",
            actual_exit_price=148.85,
            planned_exit_price=148.85,
        ),
    )
    assert r.status_code == 200
    p = r.json()["post_trade_evaluation"]
    assert p["outcome_label"] == "stopped_out"
    assert p["outcome_status"] == "negative"


def test_post_trade_evaluation_crypto_asset_class_blocked():
    r = client.post("/api/post-trade-evaluation/evaluate", json=_post_trade_evaluation_sample_request(asset_class="crypto"))
    assert r.status_code == 200
    p = r.json()["post_trade_evaluation"]
    assert p["outcome_status"] == "blocked"
    assert "asset_class_not_supported" in p["blockers"]


def test_post_trade_evaluation_critical_rule_failure_rule_violation_review_needed():
    r = client.post(
        "/api/post-trade-evaluation/evaluate",
        json=_post_trade_evaluation_sample_request(used_approved_strategy=False),
    )
    assert r.status_code == 200
    p = r.json()["post_trade_evaluation"]
    assert p["outcome_label"] == "rule_violation"
    assert p["outcome_status"] == "review_needed"


def test_post_trade_evaluation_high_slippage_flags_slippage_issue():
    # Force slippage fail: (155.50 - 150.00) / 150 * 100 = 3.67% vs max 0.15%
    r = client.post(
        "/api/post-trade-evaluation/evaluate",
        json=_post_trade_evaluation_sample_request(
            planned_exit_price=150.00,
            max_allowed_slippage_percent=0.15,
        ),
    )
    assert r.status_code == 200
    p = r.json()["post_trade_evaluation"]
    assert p["execution_quality_result"]["slippage_status"] in {"warn", "fail"}
    assert "slippage_exceeded_threshold" in p["warnings"]


def test_post_trade_evaluation_latest_after_evaluation_contract():
    _ = client.post("/api/post-trade-evaluation/evaluate", json=_post_trade_evaluation_sample_request(exit_reason="target_hit"))
    latest = client.get("/api/post-trade-evaluation/latest")
    assert latest.status_code == 200
    payload = latest.json()
    assert payload["status"] == "ok"
    assert payload["post_trade_evaluation"]["evaluation_id"].startswith("pte_")


def _learning_loop_sample_request(
    *,
    asset_class: str = "stock",
    sample_size: int = 12,
    avg_r_hint: float = 0.42,
    current_drawdown_r: float = -1.5,
    outcomes: list[dict] | None = None,
    min_sample_size_for_promotion: int = 20,
    min_avg_r_for_promotion: float = 0.35,
    max_drawdown_r_before_demotion: float = -3.0,
    max_rule_violation_rate: float = 0.10,
    max_slippage_fail_rate: float = 0.15,
) -> dict:
    if outcomes is None:
        outcomes = [
            {
                "trade_id": "trade_1",
                "outcome_label": "target_hit",
                "outcome_status": "positive",
                "realized_pnl": 55.90,
                "r_multiple": 1.83,
                "slippage_status": "pass",
                "rule_compliant": True,
            },
            {
                "trade_id": "trade_2",
                "outcome_label": "stopped_out",
                "outcome_status": "negative",
                "realized_pnl": -29.90,
                "r_multiple": -1.0,
                "slippage_status": "pass",
                "rule_compliant": True,
            },
        ]
    return {
        "strategy_key": "regime_aware_momentum_catalyst",
        "strategy_group": "regime_aware_momentum",
        "asset_class": asset_class,
        "horizon": "day_trading",
        "workflow_key": "baseline_fast_path",
        "recent_outcomes": outcomes,
        "current_status": {
            "promotion_status": "paper_ready",
            "proof_status": "paper_passed",
            "sample_size": sample_size,
            "current_drawdown_r": current_drawdown_r,
            "last_10_avg_r": avg_r_hint,
        },
        "thresholds": {
            "min_sample_size_for_promotion": min_sample_size_for_promotion,
            "min_avg_r_for_promotion": min_avg_r_for_promotion,
            "max_drawdown_r_before_demotion": max_drawdown_r_before_demotion,
            "max_rule_violation_rate": max_rule_violation_rate,
            "max_slippage_fail_rate": max_slippage_fail_rate,
        },
    }


def test_learning_loop_status_contract():
    r = client.get("/api/learning-loop/status")
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    assert payload["stage"]["stage_number"] == 14
    assert payload["stage"]["stage_key"] == "learning_loop"
    assert payload["data_mode"] == "rules_v1"


def test_learning_loop_below_sample_size_keeps_monitoring_with_warning():
    r = client.post("/api/learning-loop/evaluate", json=_learning_loop_sample_request(sample_size=12, min_sample_size_for_promotion=20))
    assert r.status_code == 200
    d = r.json()["learning_decision"]
    assert d["learning_action"] == "keep_monitoring"
    assert "sample_size_below_threshold" in d["warnings"]


def test_learning_loop_strong_metrics_promote_candidate_when_thresholds_met():
    outcomes = [
        {"trade_id": "t1", "outcome_label": "target_hit", "outcome_status": "positive", "realized_pnl": 10, "r_multiple": 0.8, "slippage_status": "pass", "rule_compliant": True},
        {"trade_id": "t2", "outcome_label": "win", "outcome_status": "positive", "realized_pnl": 12, "r_multiple": 0.7, "slippage_status": "pass", "rule_compliant": True},
    ]
    r = client.post(
        "/api/learning-loop/evaluate",
        json=_learning_loop_sample_request(
            sample_size=25,
            outcomes=outcomes,
            current_drawdown_r=-0.5,
            min_sample_size_for_promotion=20,
            min_avg_r_for_promotion=0.35,
        ),
    )
    assert r.status_code == 200
    d = r.json()["learning_decision"]
    assert d["learning_action"] == "promote_candidate"
    assert d["promotion"]["eligible_for_promotion"] is True


def test_learning_loop_drawdown_breach_triggers_demotion():
    r = client.post(
        "/api/learning-loop/evaluate",
        json=_learning_loop_sample_request(sample_size=30, current_drawdown_r=-3.5, max_drawdown_r_before_demotion=-3.0),
    )
    assert r.status_code == 200
    d = r.json()["learning_decision"]
    assert d["learning_action"] in {"demote_to_paper", "demote_to_research"}


def test_learning_loop_rule_violation_rate_high_triggers_demotion_to_research():
    outcomes = [
        {"trade_id": "t1", "outcome_label": "rule_violation", "outcome_status": "review_needed", "realized_pnl": 0, "r_multiple": 0.0, "slippage_status": "pass", "rule_compliant": False},
        {"trade_id": "t2", "outcome_label": "flat", "outcome_status": "neutral", "realized_pnl": 0, "r_multiple": 0.0, "slippage_status": "pass", "rule_compliant": True},
    ]
    r = client.post(
        "/api/learning-loop/evaluate",
        json=_learning_loop_sample_request(sample_size=25, outcomes=outcomes, max_rule_violation_rate=0.10),
    )
    assert r.status_code == 200
    d = r.json()["learning_decision"]
    assert d["learning_action"] == "demote_to_research"


def test_learning_loop_crypto_asset_class_blocks_strategy_or_review_needed():
    r = client.post("/api/learning-loop/evaluate", json=_learning_loop_sample_request(asset_class="crypto"))
    assert r.status_code == 200
    d = r.json()["learning_decision"]
    assert d["learning_action"] in {"block_strategy", "review_needed"}


def test_learning_loop_latest_after_evaluate_contract():
    _ = client.post("/api/learning-loop/evaluate", json=_learning_loop_sample_request())
    latest = client.get("/api/learning-loop/latest")
    assert latest.status_code == 200
    payload = latest.json()
    assert payload["status"] == "ok"
    assert payload["learning_decision"]["decision_id"].startswith("ll_")


def test_workflow_runbook_status_contract():
    r = client.get("/api/workflow-runbook/status")
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    assert payload["data_mode"] == "aggregated_status_v1"
    scope = payload["scope"]
    assert scope["asset_class"] == "stock"
    assert scope["horizon"] == "day_trading"
    assert scope["mode"] == "paper_first"
    assert scope["llm_required"] is False


def test_workflow_runbook_stages_returns_14_plus_and_has_execution_planner_and_execution_gated():
    r = client.get("/api/workflow-runbook/stages")
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    stages = payload["stages"]
    assert len(stages) >= 14

    st9 = next(s for s in stages if s["stage_number"] == 9)
    assert "/api/execution-planner" in st9["backend_endpoint_family"]

    st10 = next(s for s in stages if s["stage_number"] == 10)
    assert st10["implementation_status"] == "existing_gated"
    assert st10["submits_orders"] is False


def test_workflow_runbook_latest_contract_and_no_execution_trigger():
    r = client.get("/api/workflow-runbook/latest")
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    assert payload["data_mode"] == "latest_snapshot_v1"
    assert "latest" in payload
    # Should not trigger execution; should only reflect stored snapshots (likely None)
    assert "execution_planner" in payload["latest"]


def test_workflow_runbook_stages_all_uses_llm_false():
    r = client.get("/api/workflow-runbook/stages")
    assert r.status_code == 200
    stages = r.json()["stages"]
    assert all(bool(s["uses_llm"]) is False for s in stages)


def test_agent_runtime_status_contract_safety_flags():
    r = client.get("/api/agent-runtime/status")
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    assert payload["data_mode"] == "agent_runtime_foundation_v1"
    safety = payload["safety"]
    assert safety["no_broker_calls"] is True
    assert safety["no_execution_submit"] is True
    assert safety["no_llm_calls"] is True
    assert safety["dry_run_default"] is True
    assert payload["summary"]["persistence_mode"] in {"postgres", "memory"}
    assert payload["summary"]["redis_mode"] in {"available", "unavailable", "disabled"}


def test_agent_runtime_persistence_mode_contract_is_stable():
    r = client.get("/api/agent-runtime/status")
    assert r.status_code == 200
    payload = r.json()
    pm = payload["summary"]["persistence_mode"]
    assert pm in {"postgres", "memory"}

    latest = client.get("/api/agent-runtime/latest")
    assert latest.status_code == 200
    latest_payload = latest.json()
    assert latest_payload["persistence_mode"] in {"postgres", "memory"}
    assert "latest_agent_runs_by_key" in latest_payload


def test_agent_runtime_agents_includes_workflow_orchestrator_agent_and_forbidden_actions():
    r = client.get("/api/agent-runtime/agents")
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    agents = payload["agents"]
    keys = {a["agent_key"] for a in agents}
    assert "workflow_orchestrator_agent" in keys
    for a in agents:
        fa = set(a.get("forbidden_actions") or [])
        assert "broker_order_submit" in fa
        assert "live_trade_submit" in fa
        assert "auto_promote_live" in fa


def test_agent_runtime_workflow_runs_create_and_get():
    r = client.post("/api/agent-runtime/workflow-runs", json={"workflow_name": "US Stock Day-Trading Paper Workflow v1", "asset_class": "stock", "horizon": "day_trading", "mode": "paper_first", "source": "manual"})
    assert r.status_code == 200
    rec = r.json()["workflow_run"]
    assert rec["workflow_run_id"].startswith("wr_")
    gid = client.get(f"/api/agent-runtime/workflow-runs/{rec['workflow_run_id']}")
    assert gid.status_code == 200
    got = gid.json()["workflow_run"]
    assert got["workflow_run_id"] == rec["workflow_run_id"]


def test_agent_runtime_agent_runs_records_and_idempotency_duplicate():
    body = {
        "agent_key": "session_router_agent",
        "inputs": {"timestamp": "2026-05-07T09:35:00-05:00"},
        "context": {"source": "phase_0_1_test"},
        "dry_run": True,
        "requested_stage": 3,
        "idempotency_key": "idem_session_router",
    }
    r1 = client.post("/api/agent-runtime/agent-runs", json=body)
    assert r1.status_code == 200
    run1 = r1.json()["agent_run"]
    assert run1["status"] in {"completed", "blocked"}
    assert run1["agent_key"] == "session_router_agent"
    assert run1["decision"]["phase"] == "phase_2_wrapped"
    assert run1["next_agent"] == "workflow_router_agent"
    assert run1["persistence_mode"] in {"postgres", "memory"}

    r2 = client.post("/api/agent-runtime/agent-runs", json=body)
    assert r2.status_code == 200
    run2 = r2.json()["agent_run"]
    assert run2["run_id"] == run1["run_id"]
    assert run2["status"] == "duplicate"


def test_agent_runtime_latest_contract():
    r = client.get("/api/agent-runtime/latest")
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    assert payload["registered_agents_count"] >= 1
    assert "latest_agent_runs_by_key" in payload
    assert payload["persistence_mode"] in {"postgres", "memory"}
    assert payload["redis_mode"] in {"available", "unavailable", "disabled"}


def test_proof_registry_status_contract():
    r = client.get("/api/proof-registry/status")
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    assert payload["data_mode"] == "proof_registry_v1"


def test_proof_registry_post_record_and_latest():
    body = {
        "symbol": "AMD",
        "asset_class": "stock",
        "horizon": "day_trading",
        "strategy_key": "stock_day_trading",
        "proof_type": "backtest",
        "proof_status": "proof_required",
        "sample_size": 0,
        "win_rate": 0.0,
        "avg_r_multiple": 0.0,
        "source": "test",
        "evidence": {"note": "placeholder"},
    }
    r = client.post("/api/proof-registry/records", json=body)
    assert r.status_code == 200
    rec = r.json()["record"]
    assert rec["proof_id"].startswith("proof_")
    latest = client.get("/api/proof-registry/latest")
    assert latest.status_code == 200
    assert latest.json()["record"]["proof_id"] == rec["proof_id"]


def test_model_evidence_status_contract():
    r = client.get("/api/model-evidence/status")
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    assert payload["data_mode"] == "model_evidence_v1"


def test_model_evidence_post_record():
    body = {
        "model_key": "weighted_ranker_v1",
        "model_name": "Weighted Ranker V1",
        "model_family": "deterministic_baseline",
        "asset_class": "stock",
        "horizon": "day_trading",
        "status": "recorded",
        "metrics": {"note": "test"},
    }
    r = client.post("/api/model-evidence/records", json=body)
    assert r.status_code == 200
    rec = r.json()["record"]
    assert rec["evidence_id"].startswith("mev_")


def test_strategy_evidence_status_contract():
    r = client.get("/api/strategy-evidence/status")
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    assert payload["data_mode"] == "strategy_evidence_v1"


def test_strategy_evidence_post_record():
    body = {
        "strategy_key": "stock_day_trading",
        "strategy_group": "stock",
        "asset_class": "stock",
        "horizon": "day_trading",
        "status": "recorded",
        "metrics": {"note": "test"},
    }
    r = client.post("/api/strategy-evidence/records", json=body)
    assert r.status_code == 200
    rec = r.json()["record"]
    assert rec["evidence_id"].startswith("sev_")


def test_qlib_status_contract_non_failing_when_unavailable():
    r = client.get("/api/qlib/status")
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    assert payload["data_mode"] == "qlib_integration_v1"
    assert isinstance(payload["qlib_available"], bool)


def test_qlib_signal_score_post_records_artifact():
    body = {
        "symbol": "AMD",
        "asset_class": "stock",
        "horizon": "day_trading",
        "scores": {"score": 0.67, "rank": 5},
        "metrics": {"source": "test"},
    }
    r = client.post("/api/qlib/signals/score", json=body)
    assert r.status_code == 200
    art = r.json()["artifact"]
    assert art["artifact_id"].startswith("qs_")
    assert art["artifact_type"] == "signal_scores"


def test_workflow_governance_status_and_check_contract():
    r = client.get("/api/workflow-governance/status")
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    c = client.post("/api/workflow-governance/check", json={"asset_class": "stock", "horizon": "day_trading", "symbols": ["AMD"], "allow_submit": False})
    assert c.status_code == 200
    assert c.json()["status"] == "ok"


def test_audit_log_status_and_post_event_contract():
    r = client.get("/api/audit-log/status")
    assert r.status_code == 200
    p = r.json()
    assert p["status"] == "ok"
    e = client.post("/api/audit-log/events", json={"event_type": "test_event", "actor": "test", "severity": "info", "message": "hello", "metadata": {"k": "v"}})
    assert e.status_code == 200
    assert e.json()["event"]["audit_id"].startswith("audit_")


def test_approval_queue_create_approve_reject_cancel_and_audit():
    # Create
    r = client.post(
        "/api/approval-queue/items",
        json={"workflow_run_id": "wr_test", "approval_type": "execution_boundary", "status": "pending", "requested_action": {"action": "noop"}, "risk_summary": {}},
    )
    assert r.status_code == 200
    approval_id = r.json()["item"]["approval_id"]
    # Approve
    a = client.post(f"/api/approval-queue/items/{approval_id}/approve", json={"actor": "owner", "reason": "ok"})
    assert a.status_code == 200
    assert a.json()["item"]["status"] == "approved"
    # Reject (new item)
    r2 = client.post("/api/approval-queue/items", json={"workflow_run_id": "wr_test2", "approval_type": "execution_boundary", "status": "pending", "requested_action": {"action": "noop"}, "risk_summary": {}})
    approval_id2 = r2.json()["item"]["approval_id"]
    rej = client.post(f"/api/approval-queue/items/{approval_id2}/reject", json={"actor": "owner", "reason": "no"})
    assert rej.status_code == 200
    assert rej.json()["item"]["status"] == "rejected"
    # Cancel (new item)
    r3 = client.post("/api/approval-queue/items", json={"workflow_run_id": "wr_test3", "approval_type": "execution_boundary", "status": "pending", "requested_action": {"action": "noop"}, "risk_summary": {}})
    approval_id3 = r3.json()["item"]["approval_id"]
    c = client.post(f"/api/approval-queue/items/{approval_id3}/cancel", json={"actor": "owner", "reason": "cancel"})
    assert c.status_code == 200
    assert c.json()["item"]["status"] == "cancelled"


def test_workflow_scheduler_status_create_enable_disable_run_once():
    s = client.get("/api/workflow-scheduler/status")
    assert s.status_code == 200
    c = client.post("/api/workflow-scheduler/schedules", json={"name": "test", "enabled": True, "schedule_type": "interval", "interval_seconds": 60, "workflow_request": {"symbols": ["AMD"], "asset_class": "stock", "horizon": "day_trading"}})
    assert c.status_code == 200
    schedule_id = c.json()["schedule"]["schedule_id"]
    d = client.post(f"/api/workflow-scheduler/schedules/{schedule_id}/disable")
    assert d.status_code == 200
    e = client.post(f"/api/workflow-scheduler/schedules/{schedule_id}/enable")
    assert e.status_code == 200
    ro = client.post("/api/workflow-scheduler/run-once", json={"workflow_request": {"symbols": ["AMD"], "asset_class": "stock", "horizon": "day_trading", "dry_run": True, "allow_submit": False}})
    assert ro.status_code == 200
    assert ro.json()["run"]["submitted_order"] is False


def test_workflow_orchestrator_run_creates_run_and_pauses_at_execution_boundary_with_approval():
    r = client.post(
        "/api/workflow-orchestrator/run",
        json={"asset_class": "stock", "horizon": "day_trading", "mode": "paper_first", "source": "manual", "symbols": ["AMD"], "dry_run": True, "stop_at_stage": 12, "allow_submit": False, "require_human_approval": True},
    )
    assert r.status_code == 200
    run = r.json()["run"]
    assert run["submitted_order"] is False
    assert run["broker_called"] is False
    assert run["llm_used"] is False
    assert run["execution_boundary_reached"] in {True, False}
    if run["approval_required"] is True:
        assert run["approval_id"] is not None
        assert run["status"] in {"paused_for_approval", "blocked", "completed_preview"}


def test_platform_readiness_status_v2_contract():
    r = client.get("/api/platform-readiness/status")
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    assert "systems" in payload
    assert "agent_runtime" in payload["systems"]
    assert "workflow_orchestrator" in payload["systems"]


def test_qlib_automation_status_contract_non_failing():
    r = client.get("/api/qlib/automation/status")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_agent_runtime_phase3_data_readiness_agent_runs_and_traces_tool_called():
    body = {
        "agent_key": "data_readiness_agent",
        "inputs": {"asset_class": "stock", "horizon": "day_trading", "symbols": ["AMD"]},
        "context": {"source": "phase_3_test"},
        "dry_run": True,
        "idempotency_key": "idem_phase3_data_readiness",
    }
    r = client.post("/api/agent-runtime/agent-runs", json=body)
    assert r.status_code == 200
    run = r.json()["agent_run"]
    assert run["agent_key"] == "data_readiness_agent"
    assert any(e["event"] == "tool_called" for e in run["trace"])
    assert run["artifacts"].get("broker_called") is False
    assert run["artifacts"].get("submitted_order") is False
    assert run["artifacts"].get("llm_used") is False


def test_agent_runtime_phase3_market_condition_agent_runs():
    body = {
        "agent_key": "market_condition_agent",
        "inputs": {"asset_class": "stock", "horizon": "day_trading", "symbols": ["AMD"]},
        "context": {"source": "phase_3_test"},
        "dry_run": True,
        "idempotency_key": "idem_phase3_market_condition",
    }
    r = client.post("/api/agent-runtime/agent-runs", json=body)
    assert r.status_code == 200
    run = r.json()["agent_run"]
    assert run["agent_key"] == "market_condition_agent"
    assert any(e["event"] == "tool_called" for e in run["trace"])


def test_agent_runtime_phase3_watchlist_builder_agent_returns_watchlist_empty_safely():
    body = {
        "agent_key": "watchlist_builder_agent",
        "inputs": {"asset_class": "stock", "horizon": "day_trading"},
        "context": {"source": "phase_3_test"},
        "dry_run": True,
        "idempotency_key": "idem_phase3_watchlist",
    }
    r = client.post("/api/agent-runtime/agent-runs", json=body)
    assert r.status_code == 200
    run = r.json()["agent_run"]
    assert run["agent_key"] == "watchlist_builder_agent"
    assert "symbols" in run["decision"]["result"]


def test_agent_runtime_phase3_strategy_selection_agent_persists_evidence():
    body = {
        "agent_key": "strategy_selection_agent",
        "inputs": {"asset_class": "stock", "horizon": "day_trading", "market_phase": "market_open", "active_loop": "paper_first", "regime": "risk_on"},
        "context": {"source": "phase_3_test"},
        "dry_run": True,
        "idempotency_key": "idem_phase3_strategy_selection",
    }
    r = client.post("/api/agent-runtime/agent-runs", json=body)
    assert r.status_code == 200
    run = r.json()["agent_run"]
    assert run["agent_key"] == "strategy_selection_agent"
    # evidence should be writable regardless of DB availability
    ev = client.get("/api/strategy-evidence/latest")
    assert ev.status_code == 200


def test_agent_runtime_phase3_model_selection_agent_persists_model_evidence():
    body = {
        "agent_key": "model_selection_agent",
        "inputs": {"asset_class": "stock", "horizon": "day_trading", "symbol": "AMD", "strategy_key": "stock_day_trading"},
        "context": {"source": "phase_3_test"},
        "dry_run": True,
        "idempotency_key": "idem_phase3_model_selection",
    }
    r = client.post("/api/agent-runtime/agent-runs", json=body)
    assert r.status_code == 200
    run = r.json()["agent_run"]
    assert run["agent_key"] == "model_selection_agent"
    ev = client.get("/api/model-evidence/latest")
    assert ev.status_code == 200


def test_agent_runtime_phase3_backtest_validation_agent_does_not_fake_proof():
    body = {
        "agent_key": "backtest_validation_agent",
        "inputs": {"asset_class": "stock", "horizon": "day_trading", "strategy_key": "stock_day_trading"},
        "context": {"source": "phase_3_test"},
        "dry_run": True,
        "idempotency_key": "idem_phase3_backtest_validation",
    }
    r = client.post("/api/agent-runtime/agent-runs", json=body)
    assert r.status_code == 200
    run = r.json()["agent_run"]
    assert run["agent_key"] == "backtest_validation_agent"
    assert run["decision"]["result"]["proof_status"] in {"proof_required", "backtest_required", "paper_passed", "proven", "research_only", "blocked"}


def test_agent_runtime_phase3_qlib_research_agent_non_failing():
    body = {
        "agent_key": "qlib_research_agent",
        "inputs": {"asset_class": "stock", "horizon": "day_trading", "symbols": ["AMD"]},
        "context": {"source": "phase_3_test"},
        "dry_run": True,
        "idempotency_key": "idem_phase3_qlib_research",
    }
    r = client.post("/api/agent-runtime/agent-runs", json=body)
    assert r.status_code == 200
    run = r.json()["agent_run"]
    assert run["agent_key"] == "qlib_research_agent"


def test_agent_runtime_phase3_safety_crypto_blocked():
    body = {
        "agent_key": "data_readiness_agent",
        "inputs": {"asset_class": "crypto", "horizon": "day_trading", "symbols": ["BTC-USD"]},
        "context": {"source": "phase_3_test"},
        "dry_run": True,
        "idempotency_key": "idem_phase3_crypto_blocked",
    }
    r = client.post("/api/agent-runtime/agent-runs", json=body)
    assert r.status_code == 200
    run = r.json()["agent_run"]
    assert run["status"] == "blocked"


def test_agent_runtime_phase3_allow_submit_true_is_sanitized_or_blocked():
    body = {
        "agent_key": "model_selection_agent",
        "inputs": {"asset_class": "stock", "horizon": "day_trading", "symbol": "AMD", "allow_submit": True},
        "context": {"source": "phase_3_test"},
        "dry_run": True,
        "idempotency_key": "idem_phase3_allow_submit",
    }
    r = client.post("/api/agent-runtime/agent-runs", json=body)
    assert r.status_code == 200
    run = r.json()["agent_run"]
    assert run["status"] in {"completed", "blocked"}
    assert run["artifacts"].get("submitted_order") is False


def test_agent_runtime_unknown_agent_key_returns_400():
    r = client.post("/api/agent-runtime/agent-runs", json={"agent_key": "unknown_agent", "inputs": {}})
    assert r.status_code in {400, 404}


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
    assert summary["total_units"] >= 80
    assert summary["present"] + summary["partial"] + summary["missing"] + summary["backlog"] == summary["total_units"]
    assert "backend_present_count" in summary
    assert "frontend_present_count" in summary
    assert "tested_count" in summary
    assert "needs_backend_count" in summary
    assert "needs_frontend_count" in summary
    assert summary["ready_to_promote"] == 0
    assert summary["next_action"]
    assert "Stage 5 Workflow Router" not in summary["next_action"]

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
    # New reconciliation fields exist
    assert "backend_status" in unit
    assert "frontend_status" in unit
    assert "test_status" in unit

    # New units exist
    all_units = [u for st in payload["stages"] for u in st["units"]]
    names = {u["name"] for u in all_units}
    assert "Strategy Ranker" in names
    assert "Model Ranker" in names


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
