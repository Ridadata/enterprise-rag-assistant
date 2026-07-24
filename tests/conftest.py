import pytest


TEST_API_KEY = "test-api-key"


@pytest.fixture(autouse=True)
def _configure_test_api_key(monkeypatch):
    """Every integration test hits an endpoint gated by require_api_key, so configure a
    known key globally rather than repeating this in every test module."""
    monkeypatch.setenv("API_KEYS", TEST_API_KEY)


@pytest.fixture(autouse=True)
def _force_mock_llm_provider(monkeypatch):
    """Tests must never make real network calls to an LLM provider, and must behave the
    same regardless of what a developer happens to have in their local .env. Explicitly
    clearing every provider API key (rather than relying on LLM_PROVIDERS=mock alone)
    means "auto" resolution also can't accidentally pick up a real provider."""
    monkeypatch.setenv("LLM_PROVIDERS", "mock")
    for key in (
        "GEMINI_API_KEY",
        "GROQ_API_KEY",
        "OPENROUTER_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
    ):
        monkeypatch.setenv(key, "")
