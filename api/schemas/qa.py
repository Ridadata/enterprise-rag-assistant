from pydantic import BaseModel, Field


class SourceCitation(BaseModel):
    document_id: str
    title: str
    chunk_id: str
    excerpt: str
    score: float = Field(ge=0.0, le=1.0)


class AskRequest(BaseModel):
    question: str = Field(min_length=3)
    user_id: str = "demo-user"
    filters: dict[str, str | list[str]] = Field(default_factory=dict)


class AskResponse(BaseModel):
    answer: str
    confidence: str
    limitations: str
    next_step: str
    sources: list[SourceCitation]

