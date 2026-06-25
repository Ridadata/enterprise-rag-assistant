from pathlib import Path

from ingestion.chunking.simple_chunker import chunk_text
from ingestion.loaders.jsonl_loader import load_jsonl


REQUIRED_FIELDS = {
    "document_id",
    "title",
    "category",
    "department",
    "source_type",
    "created_at",
    "version",
    "access_level",
    "tags",
    "content",
}


def validate_document(document: dict) -> None:
    missing = REQUIRED_FIELDS.difference(document)
    if missing:
        raise ValueError(f"Missing required fields: {sorted(missing)}")


def preview_ingestion(path: Path) -> list[dict]:
    previews: list[dict] = []
    for document in load_jsonl(path):
        validate_document(document)
        chunks = chunk_text(document["content"])
        previews.append(
            {
                "document_id": document["document_id"],
                "title": document["title"],
                "source_type": document["source_type"],
                "chunk_count": len(chunks),
            }
        )
    return previews

