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


class OpenAICompatibleProvider(LLMProvider):
    """Any backend that speaks the OpenAI chat-completions wire format: OpenAI itself,
    Groq, OpenRouter, and a local Ollama server all qualify, so one implementation
    (parameterized by base_url/api_key/model) covers all four rather than four
    near-duplicate SDK integrations."""

    def __init__(
        self,
        *,
        name: str,
        api_key: str,
        model: str,
        base_url: str,
        timeout_seconds: float,
        require_api_key: bool = True,
    ) -> None:
        if require_api_key and not api_key:
            raise ProviderError(
                f"{name.upper()}_API_KEY is not configured.", provider=name, retryable=False
            )
        self.name = name
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds

    def _client(self):
        try:
            import openai
        except ImportError as exc:
            raise ProviderError(
                "Install the OpenAI SDK first: python -m pip install openai",
                provider=self.name,
                retryable=False,
            ) from exc
        return openai, openai.OpenAI(
            api_key=self.api_key or "unused",
            base_url=self.base_url,
            timeout=self.timeout_seconds,
        )

    def _wrap_error(self, openai_module, exc: Exception) -> ProviderError:
        if isinstance(exc, openai_module.AuthenticationError):
            return ProviderError(
                f"{self.name} authentication failed: {exc}", provider=self.name, retryable=False
            )
        if isinstance(exc, openai_module.BadRequestError):
            # Almost always an invalid model name/parameter -- won't succeed on retry.
            return ProviderError(
                f"{self.name} rejected the request: {exc}", provider=self.name, retryable=False
            )
        status = getattr(exc, "status_code", None)
        retryable = status in _RETRYABLE_STATUS_CODES if status is not None else True
        return ProviderError(
            f"{self.name} request failed: {exc}",
            provider=self.name,
            retryable=retryable,
            retry_after=_retry_after(exc),
        )

    def generate(self, system_prompt: str, user_prompt: str, fallback_text: str) -> LLMResult:
        del fallback_text
        openai_module, client = self._client()
        try:
            completion = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as exc:
            raise self._wrap_error(openai_module, exc) from exc

        usage = completion.usage
        return LLMResult(
            text=completion.choices[0].message.content or "",
            model_name=self.model,
            tokens_in=usage.prompt_tokens if usage else None,
            tokens_out=usage.completion_tokens if usage else None,
            # Pricing varies by model/provider/tier and changes over time; left
            # unestimated rather than baking in a number that would silently go stale.
            cost_estimate=None,
            is_extractive_fallback=False,
        )

    def generate_stream(self, system_prompt: str, user_prompt: str, fallback_text: str) -> Iterator[str]:
        del fallback_text
        openai_module, client = self._client()
        try:
            stream = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta
        except Exception as exc:
            raise self._wrap_error(openai_module, exc) from exc
