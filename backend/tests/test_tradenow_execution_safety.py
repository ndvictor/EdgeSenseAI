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


def test_tradenow_live_mode_cannot_be_enabled_without_env_flag():
    config = update_trade_now_config(TradeNowConfigUpdate(user_enabled=True, execution_mode="live"))
    assert config.execution_mode == "disabled"
    assert config.live_trading_enabled_env is False
