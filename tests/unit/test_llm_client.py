import pytest

from generation import llm_client
from generation.llm_client import _resolve_chain_names
from database.settings import get_settings


def test_mock_provider_echoes_fallback_text_deterministically() -> None:
    result = llm_client.generate(
        "system prompt", "user prompt", fallback_text="Based on sources: do X.", provider="mock"
    )

    assert result.text == "Based on sources: do X."
    assert result.is_extractive_fallback is True
    assert result.cost_estimate == 0.0
    assert result.tokens_in and result.tokens_out


def test_unknown_provider_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        llm_client.generate("system", "user", fallback_text="fallback", provider="not-a-real-provider")


def test_generate_falls_back_to_mock_when_no_providers_are_configured() -> None:
    # conftest.py's autouse fixture already clears every provider API key and pins
    # LLM_PROVIDERS=mock, so this exercises the same zero-config path a fresh install
    # would hit before any key is ever added.
    result = llm_client.generate("system", "user", fallback_text="the fallback")

    assert result.text == "the fallback"
    assert result.is_extractive_fallback is True


def test_generate_stream_falls_back_to_mock_when_no_providers_are_configured() -> None:
    chunks = list(llm_client.generate_stream("system", "user", fallback_text="the fallback"))

    assert chunks == ["the fallback"]


def test_auto_resolution_includes_only_providers_with_a_configured_key(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDERS", "auto")
    monkeypatch.setenv("GROQ_API_KEY", "fake-groq-key")
    # GEMINI_API_KEY stays cleared by the autouse fixture.

    names = _resolve_chain_names(get_settings())

    assert names == ["groq", "mock"]


def test_auto_resolution_prefers_gemini_over_groq_when_both_configured(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDERS", "auto")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
    monkeypatch.setenv("GROQ_API_KEY", "fake-groq-key")

    names = _resolve_chain_names(get_settings())

    assert names == ["gemini", "groq", "mock"]


def test_auto_resolution_falls_back_to_just_mock_when_nothing_configured() -> None:
    names = _resolve_chain_names(get_settings())

    assert names == ["mock"]


def test_explicit_chain_overrides_auto_order(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDERS", "groq,gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
    monkeypatch.setenv("GROQ_API_KEY", "fake-groq-key")

    names = _resolve_chain_names(get_settings())

    assert names == ["groq", "gemini", "mock"]


def test_mock_is_always_appended_even_if_omitted(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDERS", "gemini")

    names = _resolve_chain_names(get_settings())

    assert names[-1] == "mock"


def test_ollama_is_never_auto_activated(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDERS", "auto")
    # Ollama has no API key setting to check "is this configured?" against, so "auto"
    # must never include it -- only an explicit LLM_PROVIDERS=ollama,... opts in.
    names = _resolve_chain_names(get_settings())

    assert "ollama" not in names
