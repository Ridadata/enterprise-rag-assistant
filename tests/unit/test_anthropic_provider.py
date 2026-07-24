import sys
import types

import pytest

from generation.providers.anthropic_provider import AnthropicProvider
from generation.providers.base import ProviderError


class _FakeAuthenticationError(Exception):
    pass


class _FakeBadRequestError(Exception):
    pass


class _FakeAPIError(Exception):
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


def _install_fake_anthropic(monkeypatch, *, create=None, stream_cm=None, captured: dict | None = None):
    class _Messages:
        @staticmethod
        def create(**kwargs):
            if captured is not None:
                captured.update(kwargs)
            return create(**kwargs)

        @staticmethod
        def stream(**kwargs):
            return stream_cm(**kwargs)

    class _FakeAnthropicClient:
        def __init__(self, api_key=None, timeout=None):
            if captured is not None:
                captured["api_key"] = api_key
                captured["timeout"] = timeout
            self.messages = _Messages()

    fake_module = types.ModuleType("anthropic")
    fake_module.Anthropic = _FakeAnthropicClient
    fake_module.AuthenticationError = _FakeAuthenticationError
    fake_module.BadRequestError = _FakeBadRequestError
    monkeypatch.setitem(sys.modules, "anthropic", fake_module)


def test_missing_api_key_raises_non_retryable_provider_error() -> None:
    with pytest.raises(ProviderError) as exc_info:
        AnthropicProvider(api_key="", model="claude-sonnet-5", timeout_seconds=30)

    assert exc_info.value.retryable is False


def test_generate_maps_response_to_llm_result(monkeypatch) -> None:
    captured: dict = {}

    def create(**kwargs):
        return types.SimpleNamespace(
            content=[types.SimpleNamespace(type="text", text="Claude's answer.")],
            usage=types.SimpleNamespace(input_tokens=120, output_tokens=40),
        )

    _install_fake_anthropic(monkeypatch, create=create, captured=captured)
    provider = AnthropicProvider(api_key="fake-key", model="claude-sonnet-5", timeout_seconds=12.5)

    result = provider.generate("system", "user", fallback_text="fallback")

    assert result.text == "Claude's answer."
    assert result.tokens_in == 120
    assert result.tokens_out == 40
    assert captured["timeout"] == 12.5


def test_authentication_error_is_not_retryable(monkeypatch) -> None:
    def create(**kwargs):
        raise _FakeAuthenticationError("invalid key")

    _install_fake_anthropic(monkeypatch, create=create)
    provider = AnthropicProvider(api_key="fake-key", model="claude-sonnet-5", timeout_seconds=30)

    with pytest.raises(ProviderError) as exc_info:
        provider.generate("system", "user", fallback_text="fallback")

    assert exc_info.value.retryable is False


def test_rate_limit_status_code_is_retryable(monkeypatch) -> None:
    def create(**kwargs):
        raise _FakeAPIError("rate limited", status_code=429)

    _install_fake_anthropic(monkeypatch, create=create)
    provider = AnthropicProvider(api_key="fake-key", model="claude-sonnet-5", timeout_seconds=30)

    with pytest.raises(ProviderError) as exc_info:
        provider.generate("system", "user", fallback_text="fallback")

    assert exc_info.value.retryable is True


def test_generate_stream_yields_text_deltas(monkeypatch) -> None:
    class _FakeStreamContextManager:
        def __init__(self, chunks):
            self.text_stream = iter(chunks)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def stream_cm(**kwargs):
        return _FakeStreamContextManager(["Hello", " world"])

    _install_fake_anthropic(monkeypatch, stream_cm=stream_cm)
    provider = AnthropicProvider(api_key="fake-key", model="claude-sonnet-5", timeout_seconds=30)

    chunks = list(provider.generate_stream("system", "user", fallback_text="fallback"))

    assert chunks == ["Hello", " world"]


def test_missing_sdk_raises_non_retryable_provider_error(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "anthropic", None)
    provider = AnthropicProvider(api_key="fake-key", model="claude-sonnet-5", timeout_seconds=30)

    with pytest.raises(ProviderError) as exc_info:
        provider.generate("system", "user", fallback_text="fallback")

    assert exc_info.value.retryable is False
