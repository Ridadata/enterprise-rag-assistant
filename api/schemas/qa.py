from pydantic import BaseModel, Field, field_validator

from retrieval.vector_search import ALLOWED_FILTER_KEYS


class SourceCitation(BaseModel):
    document_id: str
    title: str
    chunk_id: str
    excerpt: str
    score: float = Field(ge=0.0, le=1.0)


class AskRequest(BaseModel):
    question: str = Field(min_length=3)
    # A caller-supplied label used only for logging/attribution (see queries.user_id) --
    # NOT an authenticated identity. The actual trust boundary for this endpoint is the
    # X-API-Key header (see api/security.py); this field is trusted no further than "the
    # caller says this request is on behalf of X."
    user_id: str = "demo-user"
    filters: dict[str, str | list[str]] = Field(default_factory=dict)

    @field_validator("filters")
    @classmethod
    def _reject_unknown_filter_keys(
        cls, filters: dict[str, str | list[str]]
    ) -> dict[str, str | list[str]]:
        unknown = set(filters) - ALLOWED_FILTER_KEYS
        if unknown:
            raise ValueError(
                f"Unsupported filter key(s): {sorted(unknown)}. "
                f"Allowed: {sorted(ALLOWED_FILTER_KEYS)}"
            )
        return filters


class AskResponse(BaseModel):
    answer: str
    confidence: str
    limitations: str
    next_step: str
    sources: list[SourceCitation]
    # Populated progressively: model_name is known at generation time (see
    # generation/answer_generator.py); latency_ms only once the full retrieve+generate
    # round trip completes (see api/services/rag_service.py). Defaults exist purely so
    # each layer can construct the response with what it knows at that point -- by the
    # time a response is actually returned to a client, both are always the real values.
    latency_ms: int = 0
    model_name: str = ""

