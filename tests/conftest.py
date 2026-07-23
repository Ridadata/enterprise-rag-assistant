import pytest


TEST_API_KEY = "test-api-key"


@pytest.fixture(autouse=True)
def _configure_test_api_key(monkeypatch):
    """Every integration test hits an endpoint gated by require_api_key, so configure a
    known key globally rather than repeating this in every test module."""
    monkeypatch.setenv("API_KEYS", TEST_API_KEY)
