import logging
from dataclasses import dataclass

from database.settings import get_settings


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMResult:
    text: str
    model_name: str
    tokens_in: int | None
    tokens_out: int | None
    cost_estimate: float | None
    is_extractive_fallback: bool


def _estimate_tokens(text: str) -> int:
    """~4 chars/token heuristic, consistent with ingestion/chunking/simple_chunker.py."""
    return max(1, round(len(text) / 4)) if text else 0


def _mock_generate(system_prompt: str, user_prompt: str, fallback_text: str) -> LLMResult:
    del system_prompt, user_prompt  # the mock provider just echoes the extractive fallback
    return LLMResult(
        text=fallback_text,
        model_name=get_settings().llm_model or "mock-grounded-answer",
        tokens_in=_estimate_tokens(fallback_text),
        tokens_out=_estimate_tokens(fallback_text),
        cost_estimate=0.0,
        is_extractive_fallback=True,
    )


def _anthropic_generate(system_prompt: str, user_prompt: str) -> LLMResult:
    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError("Install the Anthropic SDK first: python -m pip install anthropic") from exc

    model_name = get_settings().llm_model
    client = anthropic.Anthropic(timeout=get_settings().llm_timeout_seconds)
    message = client.messages.create(
        model=model_name,
        max_tokens=800,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = "".join(block.text for block in message.content if getattr(block, "type", None) == "text")
    return LLMResult(
        text=text,
        model_name=model_name,
        tokens_in=message.usage.input_tokens,
        tokens_out=message.usage.output_tokens,
        # Pricing varies by model/tier and changes over time; left unestimated here rather
        # than baking in a number that would silently go stale.
        cost_estimate=None,
        is_extractive_fallback=False,
    )


def _openai_generate(system_prompt: str, user_prompt: str) -> LLMResult:
    try:
        import openai
    except ImportError as exc:
        raise RuntimeError("Install the OpenAI SDK first: python -m pip install openai") from exc

    model_name = get_settings().llm_model
    client = openai.OpenAI(timeout=get_settings().llm_timeout_seconds)
    completion = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    text = completion.choices[0].message.content or ""
    usage = completion.usage
    return LLMResult(
        text=text,
        model_name=model_name,
        tokens_in=usage.prompt_tokens if usage else None,
        tokens_out=usage.completion_tokens if usage else None,
        cost_estimate=None,
        is_extractive_fallback=False,
    )


_REAL_PROVIDERS = {
    "anthropic": _anthropic_generate,
    "openai": _openai_generate,
}


def generate(
    system_prompt: str,
    user_prompt: str,
    *,
    fallback_text: str,
    provider: str | None = None,
) -> LLMResult:
    """Generate an answer via the configured LLM_PROVIDER.

    "mock" (the default) deterministically returns `fallback_text` so tests and offline
    dev never need network access or API keys. Real providers are lazily imported and,
    if they raise for any reason (missing SDK/key, network, rate limit), we log and fall
    back to the extractive text rather than turning a demo question into a 500.
    """
    key = (provider or get_settings().llm_provider).lower()
    if key == "mock":
        return _mock_generate(system_prompt, user_prompt, fallback_text)

    try:
        handler = _REAL_PROVIDERS[key]
    except KeyError:
        raise ValueError(
            f"Unknown LLM_PROVIDER {key!r}; expected one of {['mock', *sorted(_REAL_PROVIDERS)]}"
        ) from None

    try:
        return handler(system_prompt, user_prompt)
    except Exception:
        logger.exception("LLM provider %r failed; falling back to extractive answer.", key)
        return LLMResult(
            text=fallback_text,
            model_name=f"{key}-fallback-extractive",
            tokens_in=_estimate_tokens(fallback_text),
            tokens_out=_estimate_tokens(fallback_text),
            cost_estimate=0.0,
            is_extractive_fallback=True,
        )
