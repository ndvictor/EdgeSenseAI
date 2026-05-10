"""End-to-end API chain rejects non-runtime data sources."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_e2e_event_scanner_then_signal_scoring() -> None:
    scan = client.post(
        "/api/event-scanner/run",
        json={
            "symbols": ["TEST_STOCK_D"],
            "use_active_trigger_rules": False,
            "use_latest_watchlist": False,
            "source": "non_real",
            "horizon": "swing",
        },
    )
    assert scan.status_code == 422

