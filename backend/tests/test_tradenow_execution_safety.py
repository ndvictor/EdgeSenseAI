from fastapi.testclient import TestClient

from app.main import app
from app.services.alpaca_execution_service import TradeNowConfigUpdate, update_trade_now_config

client = TestClient(app)


def test_tradenow_config_defaults_safe():
    response = client.get("/api/tradenow/config")
    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_mode"] in {"dry_run", "disabled"}
    assert payload["require_human_approval"] is True
    assert payload["live_trading_enabled_env"] is False
    assert payload["broker_execution_enabled_env"] is False
    assert payload["autonomous_execution_enabled_env"] is False
    assert payload["automatic_execution_user_enabled"] is False


def test_tradenow_order_dry_run_does_not_require_broker_keys():
    update_trade_now_config(TradeNowConfigUpdate(user_enabled=True, execution_mode="dry_run"))
    response = client.post(
        "/api/tradenow/orders",
        json={
            "symbol": "AAPL",
            "side": "buy",
            "qty": 1,
            "type": "market",
            "time_in_force": "day",
            "dry_run": True,
            "human_approval_confirmed": True,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "dry_run"
    assert payload["broker_response"] is None
    assert payload["asset_class"] == "stock"
    assert payload["submitted_payload"]["symbol"] == "AAPL"


def test_tradenow_order_blocks_without_human_approval():
    update_trade_now_config(TradeNowConfigUpdate(user_enabled=True, execution_mode="dry_run"))
    response = client.post(
        "/api/tradenow/orders",
        json={
            "symbol": "AAPL",
            "side": "buy",
            "qty": 1,
            "type": "market",
            "dry_run": True,
            "human_approval_confirmed": False,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "blocked"
    assert any("Human approval" in blocker for blocker in payload["blockers"])


def test_tradenow_supports_alpaca_paper_asset_classes_in_dry_run():
    update_trade_now_config(TradeNowConfigUpdate(user_enabled=True, execution_mode="dry_run"))
    examples = [
        {"asset_class": "stock", "symbol": "AAPL", "time_in_force": "day"},
        {"asset_class": "etf", "symbol": "SPY", "time_in_force": "day"},
        {"asset_class": "crypto", "symbol": "BTC/USD", "time_in_force": "gtc"},
        {"asset_class": "option", "symbol": "AAPL260116C00200000", "time_in_force": "day", "type": "limit", "limit_price": 1.25},
    ]
    for example in examples:
        response = client.post(
            "/api/tradenow/orders",
            json={
                "symbol": example["symbol"],
                "asset_class": example["asset_class"],
                "side": "buy",
                "qty": 1,
                "type": example.get("type", "market"),
                "time_in_force": example["time_in_force"],
                "limit_price": example.get("limit_price"),
                "dry_run": True,
                "human_approval_confirmed": True,
                "approval_source": "human",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "dry_run"
        assert payload["asset_class"] == example["asset_class"]
        assert payload["broker_response"] is None


def test_crypto_rejects_day_time_in_force():
    update_trade_now_config(TradeNowConfigUpdate(user_enabled=True, execution_mode="dry_run"))
    response = client.post(
        "/api/tradenow/orders",
        json={
            "symbol": "BTC/USD",
            "asset_class": "crypto",
            "side": "buy",
            "qty": 1,
            "type": "market",
            "time_in_force": "day",
            "dry_run": True,
            "human_approval_confirmed": True,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "blocked"
    assert any("Crypto paper orders" in blocker for blocker in payload["blockers"])


def test_tradenow_live_mode_cannot_be_enabled_without_env_flag():
    config = update_trade_now_config(TradeNowConfigUpdate(user_enabled=True, execution_mode="live"))
    assert config.execution_mode == "disabled"
    assert config.live_trading_enabled_env is False


def test_autonomous_execution_defaults_blocked():
    update_trade_now_config(
        TradeNowConfigUpdate(
            user_enabled=True,
            automatic_execution_user_enabled=False,
            execution_mode="dry_run",
        )
    )
    response = client.post(
        "/api/tradenow/autonomous/orders",
        json={
            "source": "strategy_workflow",
            "workflow_run_id": "workflow-test-1",
            "recommendation_id": "rec-test-1",
            "strategy_key": "stock_day_trading",
            "symbol": "AAPL",
            "side": "buy",
            "qty": 1,
            "type": "market",
            "time_in_force": "day",
            "dry_run": True,
            "risk_gate_passed": True,
            "execution_readiness_passed": True,
            "human_approval_confirmed": True,
            "approved_by": "victor",
            "confidence_score": 0.91,
            "max_loss_dollars": 10,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["autonomous"] is True
    assert payload["status"] == "blocked"
    assert payload["autonomous_gate_status"] == "blocked"
    assert any("Automatic execution" in blocker for blocker in payload["blockers"])
    assert payload["broker_response"] is None


def test_autonomous_execution_requires_risk_gate_and_readiness():
    update_trade_now_config(
        TradeNowConfigUpdate(
            user_enabled=True,
            automatic_execution_user_enabled=True,
            execution_mode="dry_run",
        )
    )
    response = client.post(
        "/api/tradenow/autonomous/orders",
        json={
            "source": "strategy_workflow",
            "workflow_run_id": "workflow-test-2",
            "strategy_key": "stock_day_trading",
            "symbol": "AAPL",
            "side": "buy",
            "qty": 1,
            "type": "market",
            "time_in_force": "day",
            "dry_run": True,
            "risk_gate_passed": False,
            "execution_readiness_passed": False,
            "human_approval_confirmed": True,
            "approved_by": "victor",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "blocked"
    assert any("Risk gate" in blocker for blocker in payload["blockers"])
    assert any("Execution readiness" in blocker for blocker in payload["blockers"])


def test_autonomous_execution_dry_run_when_all_request_gates_pass_but_env_blocks_broker():
    update_trade_now_config(
        TradeNowConfigUpdate(
            user_enabled=True,
            automatic_execution_user_enabled=True,
            execution_mode="dry_run",
        )
    )
    response = client.post(
        "/api/tradenow/autonomous/orders",
        json={
            "source": "meta_controller",
            "workflow_run_id": "workflow-test-3",
            "recommendation_id": "rec-test-3",
            "strategy_key": "stock_day_trading",
            "symbol": "AAPL",
            "side": "buy",
            "qty": 1,
            "type": "market",
            "time_in_force": "day",
            "dry_run": True,
            "risk_gate_passed": True,
            "execution_readiness_passed": True,
            "human_approval_confirmed": True,
            "approved_by": "victor",
            "confidence_score": 0.95,
            "max_loss_dollars": 10,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"dry_run", "blocked"}
    assert payload["broker_response"] is None
    assert payload["risk_gate_passed"] is True
    assert payload["execution_readiness_passed"] is True
    assert payload["human_approval_confirmed"] is True
    assert payload["source"] == "meta_controller"


def test_autonomous_future_path_preserves_asset_class_and_gates():
    update_trade_now_config(
        TradeNowConfigUpdate(
            user_enabled=True,
            automatic_execution_user_enabled=True,
            execution_mode="dry_run",
        )
    )
    response = client.post(
        "/api/tradenow/autonomous/orders",
        json={
            "source": "scanner_trigger",
            "workflow_run_id": "workflow-crypto-1",
            "strategy_key": "crypto_intraday",
            "symbol": "BTC/USD",
            "asset_class": "crypto",
            "side": "buy",
            "qty": 0.01,
            "type": "market",
            "time_in_force": "gtc",
            "dry_run": True,
            "risk_gate_passed": True,
            "execution_readiness_passed": True,
            "human_approval_confirmed": True,
            "approval_source": "human",
            "approved_by": "victor",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["autonomous"] is True
    assert payload["asset_class"] == "crypto"
    assert payload["source"] == "scanner_trigger"
    assert payload["broker_response"] is None
