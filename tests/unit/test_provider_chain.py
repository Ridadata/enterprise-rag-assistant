import pytest

from generation.providers.base import LLMProvider, LLMResult, ProviderError
from generation.providers.chain import ProviderChain


def _no_sleep(seconds: float) -> None:
    del seconds


class _FakeProvider(LLMProvider):
    def __init__(self, name: str, *, fail: bool = False, retryable: bool = False):
        self.name = name
        self.fail = fail
        self.retryable = retryable
        self.calls = 0

    def generate(self, system_prompt, user_prompt, fallback_text):
        self.calls += 1
        if self.fail:
            raise ProviderError(f"{self.name} failed", provider=self.name, retryable=self.retryable)
        return LLMResult(
            text=f"answer from {self.name}",
            model_name=self.name,
            tokens_in=1,
            tokens_out=1,
            cost_estimate=None,
            is_extractive_fallback=False,
        )

    def generate_stream(self, system_prompt, user_prompt, fallback_text):
        self.calls += 1
        if self.fail:
            raise ProviderError(f"{self.name} failed", provider=self.name, retryable=self.retryable)
        yield f"answer from {self.name}"


def _chain(*providers: _FakeProvider) -> ProviderChain:
    factories = [(p.name, (lambda p=p: p)) for p in providers]
    return ProviderChain(factories, max_retries=0, retry_base_delay=0.01)


def test_first_provider_succeeds_others_untried() -> None:
    first = _FakeProvider("first")
    second = _FakeProvider("second")

    result = _chain(first, second).generate("sys", "user", "fallback")

    assert result.model_name == "first"
    assert first.calls == 1
    assert second.calls == 0


def test_falls_through_to_next_provider_on_failure() -> None:
    first = _FakeProvider("first", fail=True, retryable=False)
    second = _FakeProvider("second")

    result = _chain(first, second).generate("sys", "user", "fallback")

    assert result.model_name == "second"
    assert first.calls == 1
    assert second.calls == 1


def test_all_providers_failing_returns_extractive_fallback_not_raise() -> None:
    first = _FakeProvider("first", fail=True)
    second = _FakeProvider("second", fail=True)

    result = _chain(first, second).generate("sys", "user", "the fallback text")

    assert result.text == "the fallback text"
    assert result.is_extractive_fallback is True


def test_empty_chain_rejected() -> None:
    with pytest.raises(ValueError):
        ProviderChain([], max_retries=0, retry_base_delay=0.01)


def test_stream_falls_through_on_start_failure() -> None:
    first = _FakeProvider("first", fail=True, retryable=False)
    second = _FakeProvider("second")

    chunks = list(_chain(first, second).generate_stream("sys", "user", "fallback"))

    assert chunks == ["answer from second"]


def test_stream_all_providers_failing_yields_fallback_text() -> None:
    first = _FakeProvider("first", fail=True)

    chunks = list(_chain(first).generate_stream("sys", "user", "the fallback text"))

    assert chunks == ["the fallback text"]


def test_lazy_construction_failure_is_treated_like_a_call_failure() -> None:
    def _broken_factory():
        raise ProviderError("no API key configured", provider="broken", retryable=False)

    working = _FakeProvider("working")
    chain = ProviderChain(
        [("broken", _broken_factory), ("working", lambda: working)],
        max_retries=0,
        retry_base_delay=0.01,
    )

    result = chain.generate("sys", "user", "fallback")

    assert result.model_name == "working"
