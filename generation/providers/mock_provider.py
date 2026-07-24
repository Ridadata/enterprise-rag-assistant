from collections.abc import Iterator

from generation.providers.base import LLMProvider, LLMResult


def _estimate_tokens(text: str) -> int:
    """~4 chars/token heuristic, consistent with ingestion/chunking/simple_chunker.py."""
    return max(1, round(len(text) / 4)) if text else 0


class MockProvider(LLMProvider):
    """Deterministically echoes the extractive fallback text -- no network, no API key,
    never fails. Used as the default chain's guaranteed last resort and throughout the
    test suite."""

    name = "mock"

    def __init__(self, model_name: str = "mock-grounded-answer") -> None:
        self.model_name = model_name

    def generate(self, system_prompt: str, user_prompt: str, fallback_text: str) -> LLMResult:
        del system_prompt, user_prompt
        return LLMResult(
            text=fallback_text,
            model_name=self.model_name,
            tokens_in=_estimate_tokens(fallback_text),
            tokens_out=_estimate_tokens(fallback_text),
            cost_estimate=0.0,
            is_extractive_fallback=True,
        )

    def generate_stream(self, system_prompt: str, user_prompt: str, fallback_text: str) -> Iterator[str]:
        del system_prompt, user_prompt
        yield fallback_text
