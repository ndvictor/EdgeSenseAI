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


