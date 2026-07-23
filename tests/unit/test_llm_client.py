import sys
import types

import pytest

from generation import llm_client


def test_mock_provider_echoes_fallback_text_deterministically() -> None:
    result = llm_client.generate(
        "system prompt", "user prompt", fallback_text="Based on sources: do X.", provider="mock"
    )

    assert result.text == "Based on sources: do X."
    assert result.is_extractive_fallback is True
    assert result.cost_estimate == 0.0
    assert result.tokens_in and result.tokens_out


def test_unknown_provider_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
        llm_client.generate("system", "user", fallback_text="fallback", provider="not-a-real-provider")


def test_anthropic_provider_success_passes_configured_timeout(monkeypatch) -> None:
    captured = {}

    class _FakeMessage:
        content = [types.SimpleNamespace(type="text", text="Real answer from Claude.")]
        usage = types.SimpleNamespace(input_tokens=120, output_tokens=40)

    class _FakeAnthropicClient:
        def __init__(self, timeout=None):
            captured["timeout"] = timeout
            self.messages = types.SimpleNamespace(create=lambda **kwargs: _FakeMessage())

    fake_module = types.ModuleType("anthropic")
    fake_module.Anthropic = _FakeAnthropicClient
    monkeypatch.setitem(sys.modules, "anthropic", fake_module)
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "12.5")
    monkeypatch.setenv("LLM_MODEL", "claude-fake")

    result = llm_client.generate("system", "user", fallback_text="fallback", provider="anthropic")

    assert result.text == "Real answer from Claude."
    assert result.is_extractive_fallback is False
    assert result.tokens_in == 120
    assert result.tokens_out == 40
    assert captured["timeout"] == 12.5


def test_real_provider_failure_falls_back_to_extractive_text(monkeypatch) -> None:
    class _FakeAnthropicClient:
        def __init__(self, timeout=None):
            self.messages = types.SimpleNamespace(create=self._raise)

        @staticmethod
        def _raise(**kwargs):
            raise TimeoutError("request timed out")

    fake_module = types.ModuleType("anthropic")
    fake_module.Anthropic = _FakeAnthropicClient
    monkeypatch.setitem(sys.modules, "anthropic", fake_module)

    result = llm_client.generate("system", "user", fallback_text="fallback answer", provider="anthropic")

    assert result.text == "fallback answer"
    assert result.is_extractive_fallback is True
    assert result.cost_estimate == 0.0
    assert result.model_name == "anthropic-fallback-extractive"


def test_missing_sdk_falls_back_to_extractive_text(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "openai", None)  # simulates the package not being installed

    result = llm_client.generate("system", "user", fallback_text="fallback answer", provider="openai")

    assert result.text == "fallback answer"
    assert result.is_extractive_fallback is True
