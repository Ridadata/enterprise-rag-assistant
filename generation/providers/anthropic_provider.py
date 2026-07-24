from collections.abc import Iterator

from generation.providers.base import LLMProvider, LLMResult, ProviderError

_RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


def _retry_after(exc: Exception) -> float | None:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if not headers:
        return None
    try:
        return float(headers.get("retry-after"))
    except (TypeError, ValueError):
        return None


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str, timeout_seconds: float) -> None:
        if not api_key:
            raise ProviderError(
                "ANTHROPIC_API_KEY is not configured.", provider=self.name, retryable=False
            )
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    def _client(self):
        try:
            import anthropic
        except ImportError as exc:
            raise ProviderError(
                "Install the Anthropic SDK first: python -m pip install anthropic",
                provider=self.name,
                retryable=False,
            ) from exc
        return anthropic, anthropic.Anthropic(api_key=self.api_key, timeout=self.timeout_seconds)

    def _wrap_error(self, anthropic_module, exc: Exception) -> ProviderError:
        if isinstance(exc, anthropic_module.AuthenticationError):
            return ProviderError(
                f"anthropic authentication failed: {exc}", provider=self.name, retryable=False
            )
        if isinstance(exc, anthropic_module.BadRequestError):
            return ProviderError(
                f"anthropic rejected the request: {exc}", provider=self.name, retryable=False
            )
        status = getattr(exc, "status_code", None)
        retryable = status in _RETRYABLE_STATUS_CODES if status is not None else True
        return ProviderError(
            f"anthropic request failed: {exc}",
            provider=self.name,
            retryable=retryable,
            retry_after=_retry_after(exc),
        )

    def generate(self, system_prompt: str, user_prompt: str, fallback_text: str) -> LLMResult:
        del fallback_text
        anthropic_module, client = self._client()
        try:
            message = client.messages.create(
                model=self.model,
                max_tokens=800,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except Exception as exc:
            raise self._wrap_error(anthropic_module, exc) from exc

        text = "".join(block.text for block in message.content if getattr(block, "type", None) == "text")
        return LLMResult(
            text=text,
            model_name=self.model,
            tokens_in=message.usage.input_tokens,
            tokens_out=message.usage.output_tokens,
            cost_estimate=None,
            is_extractive_fallback=False,
        )

    def generate_stream(self, system_prompt: str, user_prompt: str, fallback_text: str) -> Iterator[str]:
        del fallback_text
        anthropic_module, client = self._client()
        try:
            with client.messages.stream(
                model=self.model,
                max_tokens=800,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            ) as stream:
                yield from stream.text_stream
        except Exception as exc:
            raise self._wrap_error(anthropic_module, exc) from exc
