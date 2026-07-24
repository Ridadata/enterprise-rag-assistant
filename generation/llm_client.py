from collections.abc import Callable, Iterator

from database.settings import Settings, get_settings
from generation.providers.anthropic_provider import AnthropicProvider
from generation.providers.base import LLMProvider, LLMResult
from generation.providers.chain import ProviderChain
from generation.providers.gemini_provider import GeminiProvider
from generation.providers.mock_provider import MockProvider
from generation.providers.openai_compatible_provider import OpenAICompatibleProvider

# Priority order used when LLM_PROVIDERS="auto": free-tier-friendly providers first,
# each included only if its API key is actually configured. Ollama is deliberately
# excluded from "auto" -- it's a local server, not a hosted API, so there's no key
# whose presence signals "the user wants this one"; opt in explicitly instead
# (LLM_PROVIDERS=ollama,mock).
_AUTO_ORDER = ["gemini", "groq", "openrouter", "openai", "anthropic"]

_KNOWN_PROVIDERS = frozenset({*_AUTO_ORDER, "ollama", "mock"})


def _provider_factory(
    name: str, settings: Settings, *, timeout_seconds: float | None = None
) -> Callable[[], LLMProvider]:
    """Returns a zero-arg constructor for the named provider. The constructor itself
    (not this dispatch) is where a missing API key raises -- see ProviderChain's
    docstring for why that has to be lazy."""
    timeout = timeout_seconds if timeout_seconds is not None else settings.llm_timeout_seconds
    if name == "mock":
        return lambda: MockProvider()
    if name == "gemini":
        return lambda: GeminiProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            timeout_seconds=timeout,
        )
    if name == "groq":
        return lambda: OpenAICompatibleProvider(
            name="groq",
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            base_url=settings.groq_base_url,
            timeout_seconds=timeout,
        )
    if name == "openrouter":
        return lambda: OpenAICompatibleProvider(
            name="openrouter",
            api_key=settings.openrouter_api_key,
            model=settings.openrouter_model,
            base_url=settings.openrouter_base_url,
            timeout_seconds=timeout,
        )
    if name == "openai":
        return lambda: OpenAICompatibleProvider(
            name="openai",
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            base_url=settings.openai_base_url,
            timeout_seconds=timeout,
        )
    if name == "ollama":
        return lambda: OpenAICompatibleProvider(
            name="ollama",
            api_key="ollama",  # ignored by Ollama's server; the SDK just requires a non-empty string
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            timeout_seconds=timeout,
            require_api_key=False,
        )
    if name == "anthropic":
        return lambda: AnthropicProvider(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            timeout_seconds=timeout,
        )
    raise ValueError(f"Unknown LLM provider {name!r}; expected one of {sorted(_KNOWN_PROVIDERS)}")


def _resolve_chain_names(settings: Settings) -> list[str]:
    configured = settings.llm_providers.strip().lower()
    if configured == "auto":
        has_key = {
            "gemini": bool(settings.gemini_api_key),
            "groq": bool(settings.groq_api_key),
            "openrouter": bool(settings.openrouter_api_key),
            "openai": bool(settings.openai_api_key),
            "anthropic": bool(settings.anthropic_api_key),
        }
        names = [name for name in _AUTO_ORDER if has_key[name]]
    else:
        names = [name.strip() for name in configured.split(",") if name.strip()]

    if "mock" not in names:
        names.append("mock")  # guaranteed safety net -- see ProviderChain.generate()
    return names


def get_provider_chain(
    settings: Settings | None = None,
    *,
    max_retries: int | None = None,
    timeout_seconds: float | None = None,
) -> ProviderChain:
    """Builds the configured fallback chain (LLM_PROVIDERS) fresh from settings.

    Not cached: settings can change between calls (tests monkeypatch env vars;
    get_settings() itself re-reads .env every time), and constructing a provider is
    cheap -- it's just wrapping config, not opening a connection.

    `max_retries`/`timeout_seconds` override the configured defaults for this chain --
    used by callers like the query rewriter that need to fail fast rather than inheriting
    the main answer-generation call's full retry/timeout budget.
    """
    settings = settings or get_settings()
    names = _resolve_chain_names(settings)
    factories = [
        (name, _provider_factory(name, settings, timeout_seconds=timeout_seconds)) for name in names
    ]
    return ProviderChain(
        factories,
        max_retries=max_retries if max_retries is not None else settings.llm_max_retries,
        retry_base_delay=settings.llm_retry_base_delay,
    )


def _single_provider_chain(
    provider: str,
    settings: Settings,
    *,
    max_retries: int | None = None,
    timeout_seconds: float | None = None,
) -> ProviderChain:
    """Used by callers (mainly tests) that want to force one specific provider. Still
    goes through ProviderChain, and still falls back to mock if it fails, so behavior
    stays consistent with the normal auto-resolved chain."""
    factories = [
        (provider, _provider_factory(provider, settings, timeout_seconds=timeout_seconds)),
        ("mock", _provider_factory("mock", settings, timeout_seconds=timeout_seconds)),
    ]
    return ProviderChain(
        factories,
        max_retries=max_retries if max_retries is not None else settings.llm_max_retries,
        retry_base_delay=settings.llm_retry_base_delay,
    )


def generate(
    system_prompt: str,
    user_prompt: str,
    *,
    fallback_text: str,
    provider: str | None = None,
    max_retries: int | None = None,
    timeout_seconds: float | None = None,
) -> LLMResult:
    """Generate an answer via the configured provider chain (LLM_PROVIDERS).

    Tries each configured provider in order, retrying transient failures (rate limits,
    timeouts, 5xxs) before moving to the next; always ends in the mock provider, which
    deterministically returns `fallback_text` and cannot fail, so this function never
    raises and a bad/missing API key never turns a demo question into a 500.

    `provider` overrides the configured chain with exactly one named provider (plus the
    same guaranteed mock fallback) -- mainly for tests that want to exercise a single
    provider in isolation. `max_retries`/`timeout_seconds` override the configured
    defaults for just this call -- see get_provider_chain().
    """
    settings = get_settings()
    chain = (
        _single_provider_chain(
            provider, settings, max_retries=max_retries, timeout_seconds=timeout_seconds
        )
        if provider
        else get_provider_chain(settings, max_retries=max_retries, timeout_seconds=timeout_seconds)
    )
    return chain.generate(system_prompt, user_prompt, fallback_text)


def generate_stream(
    system_prompt: str,
    user_prompt: str,
    *,
    fallback_text: str,
    provider: str | None = None,
) -> Iterator[str]:
    """Streaming counterpart to generate() -- same chain, same guaranteed fallback.
    See ProviderChain.generate_stream() for how retries interact with an in-progress
    stream (short version: only before the first chunk is yielded)."""
    settings = get_settings()
    chain = _single_provider_chain(provider, settings) if provider else get_provider_chain(settings)
    yield from chain.generate_stream(system_prompt, user_prompt, fallback_text)
