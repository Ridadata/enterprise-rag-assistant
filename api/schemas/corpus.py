from pydantic import BaseModel


class CorpusSummary(BaseModel):
    document_count: int
    chunk_count: int
    source_types: dict[str, int]
