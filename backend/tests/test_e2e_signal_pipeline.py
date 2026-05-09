"""End-to-end API chain: event scanner produces events → signal scoring scores them.

Uses mock market data so it passes in CI without broker keys.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_e2e_event_scanner_then_signal_scoring() -> None:
    scan = client.post(
        "/api/event-scanner/run",
        json={
            "symbols": ["AAPL"],
            "use_active_trigger_rules": False,
            "use_latest_watchlist": False,
            "source": "mock",
            "allow_mock": True,
            "horizon": "swing",
        },
    )
    assert scan.status_code == 200, scan.text
    scan_body = scan.json()
    assert scan_body["status"] in ("completed", "partial"), scan_body
    assert scan_body["matched_events"], (
        "Expected at least one matched event from snapshot_watch path; got "
        + repr(scan_body)
    )

    score = client.post(
        "/api/signal-scoring/run",
        json={
            "use_latest_events": True,
            "allow_mock": True,
            "source": "mock",
            "horizon": "swing",
        },
    )
    assert score.status_code == 200, score.text
    score_body = score.json()
    assert score_body["status"] in ("completed", "partial"), score_body
    assert score_body["scored_signals"], score_body
    assert score_body["scored_signals"][0]["symbol"] == "AAPL"

