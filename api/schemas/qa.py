from pydantic import BaseModel, Field, field_validator

from retrieval.vector_search import ALLOWED_FILTER_KEYS


class SourceCitation(BaseModel):
    document_id: str
    title: str
    chunk_id: str
    excerpt: str
    score: float = Field(ge=0.0, le=1.0)
    # 1-based position of this chunk within its source document (e.g. "chunk 2 of 5") --
    # these documents (tickets, runbooks, wikis, ...) aren't paginated, so this is the
    # closest honest analog to a page number rather than a fabricated one.
    chunk_position: int = 1


class ConversationTurn(BaseModel):
    """One prior question/answer pair, supplied by the caller on each request so
    follow-ups can use earlier context -- there's no server-side conversation store
    (see generation/query_rewriter.py and docs/architecture.md for why that's a
    deliberate, scoped choice rather than an oversight)."""

    question: str
    answer: str


class AskRequest(BaseModel):
    question: str = Field(min_length=3)
    # A caller-supplied label used only for logging/attribution (see queries.user_id) --
    # NOT an authenticated identity. The actual trust boundary for this endpoint is the
    # X-API-Key header (see api/security.py); this field is trusted no further than "the
    # caller says this request is on behalf of X."
    user_id: str = "demo-user"
    filters: dict[str, str | list[str]] = Field(default_factory=dict)
    # Prior turns in this conversation, oldest first. Empty for a first question -- see
    # ConversationTurn and generation/query_rewriter.py for how this drives history-aware
    # retrieval on follow-ups.
    history: list[ConversationTurn] = Field(default_factory=list)

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
    # LLM-suggested next questions, parsed from the same generation call as `answer`
    # (see generation/answer_generator.py) -- empty when the mock/extractive fallback
    # answered instead of a real model, since there's no model output to draw them from.
    follow_up_questions: list[str] = Field(default_factory=list)
    # The question actually used for retrieval, after history-aware rewriting (see
    # generation/query_rewriter.py). Equal to `question` on a first turn, or whenever
    # rewriting was skipped/failed and the raw follow-up was used as-is -- exposed mainly
    # so the UI/logs can show what Nexus actually searched for.
    retrieval_query: str = ""

