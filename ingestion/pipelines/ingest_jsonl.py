import hashlib
import json
from pathlib import Path
from typing import Any

from ingestion.chunking.simple_chunker import chunk_text
from ingestion.embedding.hash_embedding import EMBEDDING_MODEL_NAME, embed_text
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


def document_checksum(document: dict[str, Any]) -> str:
    checksum_input = json.dumps(document, sort_keys=True)
    return hashlib.sha256(checksum_input.encode("utf-8")).hexdigest()


def validate_document(document: dict[str, Any]) -> None:
    missing = REQUIRED_FIELDS.difference(document)
    if missing:
        raise ValueError(f"Missing required fields: {sorted(missing)}")
    if not isinstance(document["tags"], list):
        raise ValueError("Field 'tags' must be a list")
    if not document["content"].strip():
        raise ValueError("Field 'content' cannot be empty")


def iter_chunk_records(path: Path, include_embeddings: bool = False) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for document in load_jsonl(path):
        validate_document(document)
        checksum = document_checksum(document)
        for chunk in chunk_text(document["content"], source_type=document["source_type"]):
            chunk_id = f"{document['document_id']}::{chunk.chunk_index}"
            record: dict[str, Any] = {
                "chunk_id": chunk_id,
                "document_id": document["document_id"],
                "chunk_index": chunk.chunk_index,
                "section_title": chunk.section_title,
                "content": chunk.content,
                "token_count": chunk.token_count,
                "metadata": {
                    "title": document["title"],
                    "category": document["category"],
                    "department": document["department"],
                    "source_type": document["source_type"],
                    "created_at": document["created_at"],
                    "version": document["version"],
                    "access_level": document["access_level"],
                    "tags": document["tags"],
                    "checksum": checksum,
                },
            }
            if include_embeddings:
                record["embedding_model"] = EMBEDDING_MODEL_NAME
                record["embedding"] = embed_text(chunk.content)
            records.append(record)
    return records


def preview_ingestion(path: Path) -> list[dict[str, Any]]:
    previews: list[dict[str, Any]] = []
    for document in load_jsonl(path):
        validate_document(document)
        chunks = chunk_text(document["content"], source_type=document["source_type"])
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


def export_processed_chunks(
    source_path: Path,
    output_path: Path,
    include_embeddings: bool = False,
) -> dict[str, Any]:
    records = iter_chunk_records(source_path, include_embeddings=include_embeddings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    return {
        "source_path": str(source_path),
        "output_path": str(output_path),
        "chunk_count": len(records),
        "include_embeddings": include_embeddings,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Preview JSONL ingestion without writing to storage.")
    parser.add_argument("path", type=Path, help="Path to a JSONL document dataset")
    parser.add_argument("--processed-output", type=Path)
    parser.add_argument("--with-embeddings", action="store_true")
    args = parser.parse_args()

    summary = summarize_ingestion(args.path)
    if args.processed_output:
        summary["processed_export"] = export_processed_chunks(
            source_path=args.path,
            output_path=args.processed_output,
            include_embeddings=args.with_embeddings,
        )
    print(json.dumps(summary, indent=2, sort_keys=True))
