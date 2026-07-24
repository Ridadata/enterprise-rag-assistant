import logging
from collections.abc import Callable, Iterator

from generation.providers.base import LLMProvider, LLMResult, ProviderError
from generation.providers.retry import call_with_retries, iter_with_retry_on_start

logger = logging.getLogger(__name__)


def _estimate_tokens(text: str) -> int:
    return max(1, round(len(text) / 4)) if text else 0


class ProviderChain:
    """Tries providers in priority order, retrying transient failures within each one
    (see retry.py) before moving on to the next. Provider construction is lazy --
    deferred until it's actually this provider's turn -- so a provider that fails to
    construct (e.g. its API key isn't configured) is just skipped like any other
    failure, not something that has to be avoided ahead of time.

    `provider_factories` pairs a stable name (used for logging/error messages, since a
    construction failure means there's no provider instance yet to ask for its own
    name) with a zero-arg constructor for that provider.
    """

    def __init__(
        self,
        provider_factories: list[tuple[str, Callable[[], LLMProvider]]],
        *,
        max_retries: int,
        retry_base_delay: float,
    ) -> None:
        if not provider_factories:
            raise ValueError("ProviderChain needs at least one provider")
        self.provider_factories = provider_factories
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay

    def generate(self, system_prompt: str, user_prompt: str, fallback_text: str) -> LLMResult:
        for name, factory in self.provider_factories:
            try:
                return call_with_retries(
                    lambda factory=factory: factory().generate(system_prompt, user_prompt, fallback_text),
                    provider_name=name,
                    max_retries=self.max_retries,
                    base_delay=self.retry_base_delay,
                )
            except ProviderError as exc:
                logger.warning("Provider %r unavailable, trying next in chain: %s", name, exc)
                continue

        # Unreachable when the chain ends in MockProvider (get_provider_chain() always
        # appends it) since MockProvider.generate() cannot fail -- kept as a hard floor
        # in case a chain is ever built without it, so a caller never sees a raised
        # exception from this method.
        logger.error("Every provider in the chain failed; returning the extractive fallback directly.")
        return LLMResult(
            text=fallback_text,
            model_name="fallback-extractive",
            tokens_in=_estimate_tokens(fallback_text),
            tokens_out=_estimate_tokens(fallback_text),
            cost_estimate=0.0,
            is_extractive_fallback=True,
        )

    def generate_stream(self, system_prompt: str, user_prompt: str, fallback_text: str) -> Iterator[str]:
        for name, factory in self.provider_factories:
            try:
                yield from iter_with_retry_on_start(
                    lambda factory=factory: factory().generate_stream(
                        system_prompt, user_prompt, fallback_text
                    ),
                    provider_name=name,
                    max_retries=self.max_retries,
                    base_delay=self.retry_base_delay,
                )
                return
            except ProviderError as exc:
                logger.warning("Provider %r unavailable, trying next in chain: %s", name, exc)
                continue

        logger.error("Every provider in the chain failed; yielding the extractive fallback directly.")
        yield fallback_text
