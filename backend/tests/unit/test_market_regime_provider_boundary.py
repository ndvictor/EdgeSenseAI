import pytest

from app.services.market_regime_providers import MockRegimeProvider, SourceBackedRegimeProvider, StaticPrototypeRegimeProvider, get_market_regime_provider


@pytest.mark.unit
def test_static_regime_provider_is_explicitly_not_real_data():
    response = StaticPrototypeRegimeProvider().build_regime()
    assert response.data_source == "hardcoded_prototype"
    assert response.source_type == "static_placeholder"
    assert response.real_data_used is False
    assert response.provider == "none"
    assert response.llm_used == "none"
    assert response.model_used == "none"


@pytest.mark.unit
def test_mock_regime_provider_marks_mock_source():
    response = MockRegimeProvider().build_regime()
    assert response.data_source == "mock"
    assert response.source_type == "mock"
    assert response.real_data_used is False


@pytest.mark.unit
def test_source_backed_boundary_is_not_configured_until_wired():
    response = SourceBackedRegimeProvider().build_regime()
    assert response.source_type == "not_implemented"
    assert response.provider == "not_configured"
    assert response.real_data_used is False


@pytest.mark.unit
def test_provider_factory_defaults_to_static_safely():
    assert isinstance(get_market_regime_provider(), StaticPrototypeRegimeProvider)
    assert isinstance(get_market_regime_provider("mock"), MockRegimeProvider)
    assert isinstance(get_market_regime_provider("source_backed"), SourceBackedRegimeProvider)
