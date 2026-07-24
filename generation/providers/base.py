from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMResult:
    text: str
    model_name: str
    tokens_in: int | None
    tokens_out: int | None
    cost_estimate: float | None
    is_extractive_fallback: bool


class ProviderError(Exception):
    """Raised by a provider when a call fails, carrying enough detail for the retry/
    fallback logic to decide what to do next without knowing anything SDK-specific."""

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        retryable: bool,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.retryable = retryable
        self.retry_after = retry_after


class LLMProvider(ABC):
    """A single LLM backend. Implementations translate SDK-specific exceptions into
    ProviderError so the retry/fallback chain never needs SDK-specific knowledge.

    Every method receives `fallback_text` (the extractive, non-LLM answer derived from
    retrieved chunks) even though only MockProvider actually uses it -- this keeps the
    interface uniform, so "fall back to a deterministic answer" is just "the mock
    provider" rather than special-cased chain logic, and it stays available if a real
    provider ever wants to use it (e.g. to validate/ground its own output).
    """

    name: str

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str, fallback_text: str) -> LLMResult:
        """Return a complete response. Raises ProviderError on any failure."""

    @abstractmethod
    def generate_stream(self, system_prompt: str, user_prompt: str, fallback_text: str) -> Iterator[str]:
        """Yield text deltas as they arrive. Raises ProviderError if the call fails
        before any content is yielded; once the first chunk has been yielded, the
        caller has committed to this provider (see ProviderChain.generate_stream)."""
