import sys
import types

import pytest

from generation.providers.base import ProviderError
from generation.providers.openai_compatible_provider import OpenAICompatibleProvider


class _FakeAuthenticationError(Exception):
    pass


class _FakeBadRequestError(Exception):
    pass


class _FakeAPIError(Exception):
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


def _install_fake_openai(monkeypatch, *, create=None, captured: dict | None = None):
    class _Completions:
        @staticmethod
        def create(**kwargs):
            if captured is not None:
                captured.update(kwargs)
            return create(**kwargs)

    class _Chat:
        completions = _Completions()

    class _FakeOpenAIClient:
        def __init__(self, api_key=None, base_url=None, timeout=None):
            if captured is not None:
                captured["api_key"] = api_key
                captured["base_url"] = base_url
                captured["timeout"] = timeout
            self.chat = _Chat()

    fake_module = types.ModuleType("openai")
    fake_module.OpenAI = _FakeOpenAIClient
    fake_module.AuthenticationError = _FakeAuthenticationError
    fake_module.BadRequestError = _FakeBadRequestError
    monkeypatch.setitem(sys.modules, "openai", fake_module)


def test_missing_api_key_raises_non_retryable_provider_error() -> None:
    with pytest.raises(ProviderError) as exc_info:
        OpenAICompatibleProvider(
            name="groq", api_key="", model="llama-3.3-70b-versatile", base_url="https://x", timeout_seconds=30
        )

    assert exc_info.value.retryable is False


def test_ollama_does_not_require_an_api_key() -> None:
    # Should not raise, unlike every other provider -- Ollama is a local server.
    OpenAICompatibleProvider(
        name="ollama",
        api_key="ollama",
        model="llama3.1",
        base_url="http://localhost:11434/v1",
        timeout_seconds=30,
        require_api_key=False,
    )


def test_generate_passes_base_url_and_maps_response(monkeypatch) -> None:
    captured: dict = {}

    def create(**kwargs):
        return types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="Groq's answer."))],
            usage=types.SimpleNamespace(prompt_tokens=10, completion_tokens=5),
        )

    _install_fake_openai(monkeypatch, create=create, captured=captured)
    provider = OpenAICompatibleProvider(
        name="groq",
        api_key="fake-key",
        model="llama-3.3-70b-versatile",
        base_url="https://api.groq.com/openai/v1",
        timeout_seconds=30,
    )

    result = provider.generate("system", "user", fallback_text="fallback")

    assert result.text == "Groq's answer."
    assert result.model_name == "llama-3.3-70b-versatile"
    assert result.tokens_in == 10
    assert result.tokens_out == 5
    assert captured["base_url"] == "https://api.groq.com/openai/v1"


def test_authentication_error_is_not_retryable(monkeypatch) -> None:
    def create(**kwargs):
        raise _FakeAuthenticationError("invalid key")

    _install_fake_openai(monkeypatch, create=create)
    provider = OpenAICompatibleProvider(
        name="openai", api_key="fake-key", model="gpt-4o-mini", base_url="https://x", timeout_seconds=30
    )

    with pytest.raises(ProviderError) as exc_info:
        provider.generate("system", "user", fallback_text="fallback")

    assert exc_info.value.retryable is False


def test_bad_request_error_is_not_retryable(monkeypatch) -> None:
    def create(**kwargs):
        raise _FakeBadRequestError("unknown model")

    _install_fake_openai(monkeypatch, create=create)
    provider = OpenAICompatibleProvider(
        name="openai", api_key="fake-key", model="not-a-real-model", base_url="https://x", timeout_seconds=30
    )

    with pytest.raises(ProviderError) as exc_info:
        provider.generate("system", "user", fallback_text="fallback")

    assert exc_info.value.retryable is False


def test_rate_limit_status_code_is_retryable(monkeypatch) -> None:
    def create(**kwargs):
        raise _FakeAPIError("rate limited", status_code=429)

    _install_fake_openai(monkeypatch, create=create)
    provider = OpenAICompatibleProvider(
        name="openai", api_key="fake-key", model="gpt-4o-mini", base_url="https://x", timeout_seconds=30
    )

    with pytest.raises(ProviderError) as exc_info:
        provider.generate("system", "user", fallback_text="fallback")

    assert exc_info.value.retryable is True


def test_generate_stream_yields_deltas(monkeypatch) -> None:
    def create(**kwargs):
        assert kwargs["stream"] is True
        return [
            types.SimpleNamespace(choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="Hel"))]),
            types.SimpleNamespace(choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content="lo"))]),
        ]

    _install_fake_openai(monkeypatch, create=create)
    provider = OpenAICompatibleProvider(
        name="openai", api_key="fake-key", model="gpt-4o-mini", base_url="https://x", timeout_seconds=30
    )

    chunks = list(provider.generate_stream("system", "user", fallback_text="fallback"))

    assert chunks == ["Hel", "lo"]


def test_missing_sdk_raises_non_retryable_provider_error(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "openai", None)
    provider = OpenAICompatibleProvider(
        name="openai", api_key="fake-key", model="gpt-4o-mini", base_url="https://x", timeout_seconds=30
    )

    with pytest.raises(ProviderError) as exc_info:
        provider.generate("system", "user", fallback_text="fallback")

    assert exc_info.value.retryable is False
