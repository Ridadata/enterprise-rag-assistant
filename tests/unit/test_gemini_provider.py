import sys
import types

import pytest

from generation.providers.base import ProviderError
from generation.providers.gemini_provider import GeminiProvider


def _install_fake_genai(monkeypatch, *, generate_content=None, generate_content_stream=None):
    fake_types = types.SimpleNamespace(
        HttpOptions=lambda **kwargs: kwargs,
        GenerateContentConfig=lambda **kwargs: kwargs,
    )

    class _FakeModels:
        @staticmethod
        def generate_content(**kwargs):
            return generate_content(**kwargs)

        @staticmethod
        def generate_content_stream(**kwargs):
            return generate_content_stream(**kwargs)

    class _FakeClient:
        def __init__(self, api_key=None, http_options=None):
            del api_key, http_options
            self.models = _FakeModels()

    fake_genai = types.ModuleType("google.genai")
    fake_genai.types = fake_types
    fake_genai.Client = _FakeClient

    fake_google = types.ModuleType("google")
    fake_google.genai = fake_genai

    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)


def test_missing_api_key_raises_non_retryable_provider_error() -> None:
    with pytest.raises(ProviderError) as exc_info:
        GeminiProvider(api_key="", model="gemini-2.5-flash", timeout_seconds=30)

    assert exc_info.value.retryable is False


def test_generate_maps_response_to_llm_result(monkeypatch) -> None:
    def generate_content(**kwargs):
        assert kwargs["model"] == "gemini-2.5-flash"
        return types.SimpleNamespace(
            text="Gemini's answer.",
            usage_metadata=types.SimpleNamespace(prompt_token_count=42, candidates_token_count=13),
        )

    _install_fake_genai(monkeypatch, generate_content=generate_content)
    provider = GeminiProvider(api_key="fake-key", model="gemini-2.5-flash", timeout_seconds=30)

    result = provider.generate("system", "user", fallback_text="fallback")

    assert result.text == "Gemini's answer."
    assert result.model_name == "gemini-2.5-flash"
    assert result.tokens_in == 42
    assert result.tokens_out == 13
    assert result.is_extractive_fallback is False


def test_rate_limit_error_is_retryable(monkeypatch) -> None:
    class _RateLimitError(Exception):
        code = 429

    def generate_content(**kwargs):
        raise _RateLimitError("quota exceeded")

    _install_fake_genai(monkeypatch, generate_content=generate_content)
    provider = GeminiProvider(api_key="fake-key", model="gemini-2.5-flash", timeout_seconds=30)

    with pytest.raises(ProviderError) as exc_info:
        provider.generate("system", "user", fallback_text="fallback")

    assert exc_info.value.retryable is True


def test_auth_error_is_not_retryable(monkeypatch) -> None:
    class _AuthError(Exception):
        code = 401

    def generate_content(**kwargs):
        raise _AuthError("invalid API key")

    _install_fake_genai(monkeypatch, generate_content=generate_content)
    provider = GeminiProvider(api_key="fake-key", model="gemini-2.5-flash", timeout_seconds=30)

    with pytest.raises(ProviderError) as exc_info:
        provider.generate("system", "user", fallback_text="fallback")

    assert exc_info.value.retryable is False


def test_generate_stream_yields_text_chunks(monkeypatch) -> None:
    def generate_content_stream(**kwargs):
        del kwargs
        yield types.SimpleNamespace(text="Hello")
        yield types.SimpleNamespace(text=" world")

    _install_fake_genai(monkeypatch, generate_content_stream=generate_content_stream)
    provider = GeminiProvider(api_key="fake-key", model="gemini-2.5-flash", timeout_seconds=30)

    chunks = list(provider.generate_stream("system", "user", fallback_text="fallback"))

    assert chunks == ["Hello", " world"]


def test_missing_sdk_raises_non_retryable_provider_error(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "google", None)
    monkeypatch.setitem(sys.modules, "google.genai", None)
    provider = GeminiProvider(api_key="fake-key", model="gemini-2.5-flash", timeout_seconds=30)

    with pytest.raises(ProviderError) as exc_info:
        provider.generate("system", "user", fallback_text="fallback")

    assert exc_info.value.retryable is False
