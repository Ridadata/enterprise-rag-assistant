from pathlib import Path
from typing import Any

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


def validate_document(document: dict[str, Any]) -> None:
    missing = REQUIRED_FIELDS.difference(document)
    if missing:
        raise ValueError(f"Missing required fields: {sorted(missing)}")
    if not isinstance(document["tags"], list):
        raise ValueError("Field 'tags' must be a list")
    if not document["content"].strip():
        raise ValueError("Field 'content' cannot be empty")


def preview_ingestion(path: Path) -> list[dict[str, Any]]:
    previews: list[dict[str, Any]] = []
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


def summarize_ingestion(path: Path) -> dict[str, Any]:
    previews = preview_ingestion(path)
    by_source_type: dict[str, int] = {}
    total_chunks = 0

    for preview in previews:
        by_source_type[preview["source_type"]] = by_source_type.get(preview["source_type"], 0) + 1
        total_chunks += preview["chunk_count"]

    return {
        "document_count": len(previews),
        "chunk_count": total_chunks,
        "source_types": by_source_type,
    }


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Preview JSONL ingestion without writing to storage.")
    parser.add_argument("path", type=Path, help="Path to a JSONL document dataset")
    args = parser.parse_args()

    print(json.dumps(summarize_ingestion(args.path), indent=2, sort_keys=True))
