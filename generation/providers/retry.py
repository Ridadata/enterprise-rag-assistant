import logging
import random
import time
from collections.abc import Callable, Iterator
from typing import TypeVar

from generation.providers.base import ProviderError


logger = logging.getLogger(__name__)

T = TypeVar("T")


def _backoff_seconds(attempt: int, base_delay: float) -> float:
    """Exponential backoff with full jitter: base * 2^attempt, randomized in [0, computed]
    so many concurrent requests retrying at once don't all retry in lockstep."""
    return random.uniform(0, base_delay * (2**attempt))


def call_with_retries(
    func: Callable[[], T],
    *,
    provider_name: str,
    max_retries: int,
    base_delay: float,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Invoke func(), retrying on retryable ProviderErrors up to max_retries times.

    Honors ProviderError.retry_after when the provider surfaced one (e.g. a 429's
    Retry-After header); otherwise falls back to exponential backoff with jitter.
    Non-retryable errors (bad API key, invalid model, etc.) propagate immediately --
    retrying them would just waste time before the caller falls back to the next
    provider in the chain.
    """
    last_error: ProviderError | None = None
    for attempt in range(max_retries + 1):
        try:
            return func()
        except ProviderError as exc:
            last_error = exc
            if not exc.retryable or attempt == max_retries:
                raise
            delay = exc.retry_after if exc.retry_after is not None else _backoff_seconds(attempt, base_delay)
            logger.warning(
                "Provider %r call failed (attempt %d/%d), retrying in %.2fs: %s",
                provider_name,
                attempt + 1,
                max_retries + 1,
                delay,
                exc,
            )
            sleep(delay)
    # Unreachable: the loop above always either returns or raises on the final attempt.
    assert last_error is not None
    raise last_error


def iter_with_retry_on_start(
    make_stream: Callable[[], Iterator[str]],
    *,
    provider_name: str,
    max_retries: int,
    base_delay: float,
    sleep: Callable[[float], None] = time.sleep,
) -> Iterator[str]:
    """Like call_with_retries, but for a streaming call: retries apply only to getting
    the stream started and receiving its first chunk. Once at least one chunk has
    reached the caller, a mid-stream failure propagates immediately rather than
    silently retrying (that would mean re-emitting duplicate/out-of-order text)."""

    def _start() -> tuple[Iterator[str], str]:
        stream = make_stream()
        try:
            first_chunk = next(stream)
        except StopIteration:
            # An immediately-exhausted stream (zero chunks) isn't a failure worth
            # retrying or falling back on -- treat it as a legitimate empty response.
            first_chunk = ""
        return stream, first_chunk

    stream, first_chunk = call_with_retries(
        _start,
        provider_name=provider_name,
        max_retries=max_retries,
        base_delay=base_delay,
        sleep=sleep,
    )
    yield first_chunk
    yield from stream
