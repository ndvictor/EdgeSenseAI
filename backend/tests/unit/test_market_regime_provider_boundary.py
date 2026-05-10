import pytest

from app.services.market_regime_providers import SourceBackedRegimeProvider, UnavailableRegimeProvider, get_market_regime_provider


@pytest.mark.unit
def test_unavailable_regime_provider_is_explicitly_not_real_data():
    response = UnavailableRegimeProvider().build_regime()
    assert response.data_source == "source_unavailable"
    assert response.source_type == "not_configured"
    assert response.real_data_used is False
    assert response.provider == "not_configured"
    assert response.llm_used == "none"
    assert response.model_used == "none"


@pytest.mark.unit
def test_unavailable_regime_provider_marks_unavailable_source():
    response = UnavailableRegimeProvider().build_regime()
    assert response.data_source == "source_unavailable"
    assert response.source_type == "not_configured"
    assert response.real_data_used is False


@pytest.mark.unit
def test_source_backed_boundary_is_not_configured_until_wired():
    response = SourceBackedRegimeProvider().build_regime()
    assert response.source_type == "not_configured"
    assert response.provider == "not_configured"
    assert response.real_data_used is False


@pytest.mark.unit
def test_provider_factory_defaults_to_static_safely():
    assert isinstance(get_market_regime_provider(), SourceBackedRegimeProvider)
    assert isinstance(get_market_regime_provider("not_configured"), UnavailableRegimeProvider)
    assert isinstance(get_market_regime_provider("source_backed"), SourceBackedRegimeProvider)
