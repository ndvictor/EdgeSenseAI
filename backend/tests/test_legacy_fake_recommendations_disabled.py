from __future__ import annotations

import pytest


def test_top_action_is_unavailable_placeholder_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    from app.services.recommendation_engine_service import build_top_action_recommendation

    top = build_top_action_recommendation()
    assert top.symbol == "UNAVAILABLE"
    assert top.data_mode == "source_unavailable"


def test_alternatives_empty_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    from app.services.recommendation_engine_service import build_alternative_recommendations

    assert build_alternative_recommendations() == []


def test_demo_top_action_when_mock_explicitly_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("ALLOW_MOCK_MARKET_DATA", "true")
    from app.services.recommendation_engine_service import build_top_action_recommendation

    top = build_top_action_recommendation()
    assert top.symbol == "AMD"
    assert top.final_score == 84
