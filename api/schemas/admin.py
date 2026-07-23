from datetime import date, datetime

from pydantic import BaseModel


class QueryVolumePoint(BaseModel):
    day: date
    query_count: int


class CitedDocument(BaseModel):
    document_id: str
    title: str
    citation_count: int


class IngestionStatusCount(BaseModel):
    status: str
    count: int


class AdminSummary(BaseModel):
    retrieval_backend: str
    total_queries: int
    mean_latency_ms: float | None
    p95_latency_ms: float | None
    confidence_counts: dict[str, int]
    idk_rate: float
    total_tokens_in: int
    total_tokens_out: int
    total_cost_estimate: float
    queries_by_day: list[QueryVolumePoint]
    most_cited_documents: list[CitedDocument]
    never_retrieved_document_count: int
    ingestion_status_counts: list[IngestionStatusCount]
    most_recent_ingestion_at: datetime | None
