from collections.abc import Iterator

from generation.providers.base import LLMProvider, LLMResult, ProviderError

# HTTP status codes that mean "try again later," not "this will never work."
_RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


def _status_code(exc: Exception) -> int | None:
    """google-genai's ClientError/ServerError expose the HTTP status differently across
    SDK versions (.code vs .status_code) -- check both rather than pinning to one."""
    for attribute in ("code", "status_code"):
        value = getattr(exc, attribute, None)
        if isinstance(value, int):
            return value
    return None


def _retry_after(exc: Exception) -> float | None:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if not headers:
        return None
    try:
        return float(headers.get("retry-after"))
    except (TypeError, ValueError):
        return None


def _wrap_error(exc: Exception, provider_name: str) -> ProviderError:
    status = _status_code(exc)
    retryable = status in _RETRYABLE_STATUS_CODES if status is not None else True
    return ProviderError(
        f"Gemini request failed: {exc}",
        provider=provider_name,
        retryable=retryable,
        retry_after=_retry_after(exc),
    )


class GeminiProvider(LLMProvider):
    """Google Gemini via the google-genai SDK. Free-tier friendly (the flash tier has a
    no-cost quota), the recommended default primary provider."""

    name = "gemini"

    def __init__(self, api_key: str, model: str, timeout_seconds: float) -> None:
        if not api_key:
            raise ProviderError(
                "GEMINI_API_KEY is not configured.", provider=self.name, retryable=False
            )
        self.api_key = api_key
        self.model = model
        # google-genai's HttpOptions timeout is in milliseconds.
        self.timeout_ms = int(timeout_seconds * 1000)

    def _client(self):
        try:
            from google import genai
        except ImportError as exc:
            raise ProviderError(
                "Install the Gemini SDK first: python -m pip install google-genai",
                provider=self.name,
                retryable=False,
            ) from exc
        return genai, genai.Client(
            api_key=self.api_key, http_options=genai.types.HttpOptions(timeout=self.timeout_ms)
        )

    def generate(self, system_prompt: str, user_prompt: str, fallback_text: str) -> LLMResult:
        del fallback_text
        genai, client = self._client()
        try:
            response = client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=genai.types.GenerateContentConfig(system_instruction=system_prompt),
            )
        except Exception as exc:
            raise _wrap_error(exc, self.name) from exc

        usage = response.usage_metadata
        return LLMResult(
            text=response.text or "",
            model_name=self.model,
            tokens_in=getattr(usage, "prompt_token_count", None),
            tokens_out=getattr(usage, "candidates_token_count", None),
            # Gemini's free tier has no per-token cost; a paid-tier estimate would need
            # per-model pricing wired in separately.
            cost_estimate=None,
            is_extractive_fallback=False,
        )

    def generate_stream(self, system_prompt: str, user_prompt: str, fallback_text: str) -> Iterator[str]:
        del fallback_text
        genai, client = self._client()
        try:
            stream = client.models.generate_content_stream(
                model=self.model,
                contents=user_prompt,
                config=genai.types.GenerateContentConfig(system_instruction=system_prompt),
            )
            for chunk in stream:
                if chunk.text:
                    yield chunk.text
        except Exception as exc:
            raise _wrap_error(exc, self.name) from exc
