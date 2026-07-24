import pytest

from generation.providers.base import ProviderError
from generation.providers.retry import call_with_retries, iter_with_retry_on_start


def _no_sleep(seconds: float) -> None:
    del seconds  # tests must not actually wait out backoff delays


def test_call_with_retries_returns_immediately_on_success() -> None:
    calls = []

    def func():
        calls.append(1)
        return "ok"

    result = call_with_retries(
        func, provider_name="p", max_retries=2, base_delay=0.01, sleep=_no_sleep
    )

    assert result == "ok"
    assert len(calls) == 1


def test_call_with_retries_retries_retryable_errors_then_succeeds() -> None:
    attempts = {"count": 0}

    def func():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise ProviderError("rate limited", provider="p", retryable=True)
        return "ok"

    result = call_with_retries(
        func, provider_name="p", max_retries=5, base_delay=0.01, sleep=_no_sleep
    )

    assert result == "ok"
    assert attempts["count"] == 3


def test_call_with_retries_gives_up_after_max_retries() -> None:
    attempts = {"count": 0}

    def func():
        attempts["count"] += 1
        raise ProviderError("still failing", provider="p", retryable=True)

    with pytest.raises(ProviderError):
        call_with_retries(func, provider_name="p", max_retries=2, base_delay=0.01, sleep=_no_sleep)

    assert attempts["count"] == 3  # initial attempt + 2 retries


def test_call_with_retries_does_not_retry_non_retryable_errors() -> None:
    attempts = {"count": 0}

    def func():
        attempts["count"] += 1
        raise ProviderError("bad api key", provider="p", retryable=False)

    with pytest.raises(ProviderError):
        call_with_retries(func, provider_name="p", max_retries=5, base_delay=0.01, sleep=_no_sleep)

    assert attempts["count"] == 1


def test_call_with_retries_honors_retry_after_over_backoff() -> None:
    sleeps = []

    def func():
        if len(sleeps) == 0:
            raise ProviderError("rate limited", provider="p", retryable=True, retry_after=7.5)
        return "ok"

    call_with_retries(
        func, provider_name="p", max_retries=1, base_delay=0.01, sleep=sleeps.append
    )

    assert sleeps == [7.5]


def test_iter_with_retry_on_start_retries_before_first_chunk() -> None:
    attempts = {"count": 0}

    def make_stream():
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise ProviderError("connection reset", provider="p", retryable=True)
        yield "hello"
        yield " world"

    chunks = list(
        iter_with_retry_on_start(
            make_stream, provider_name="p", max_retries=3, base_delay=0.01, sleep=_no_sleep
        )
    )

    assert chunks == ["hello", " world"]
    assert attempts["count"] == 2


def test_iter_with_retry_on_start_does_not_retry_after_first_chunk() -> None:
    def make_stream():
        yield "hello"
        raise ProviderError("mid-stream failure", provider="p", retryable=True)

    stream = iter_with_retry_on_start(
        make_stream, provider_name="p", max_retries=3, base_delay=0.01, sleep=_no_sleep
    )

    assert next(stream) == "hello"
    with pytest.raises(ProviderError):
        next(stream)


def test_iter_with_retry_on_start_handles_empty_stream() -> None:
    def make_stream():
        return
        yield  # pragma: no cover -- makes this a generator function with zero yields

    chunks = list(
        iter_with_retry_on_start(
            make_stream, provider_name="p", max_retries=1, base_delay=0.01, sleep=_no_sleep
        )
    )

    assert chunks == [""]
