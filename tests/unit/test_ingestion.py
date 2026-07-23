from pathlib import Path

import pytest

from ingestion.pipelines.ingest_jsonl import (
    export_processed_chunks,
    iter_chunk_records,
    summarize_ingestion,
    validate_document,
)


SAMPLE_DATASET = Path("data/synthetic/sample_documents.jsonl")


def test_summarize_ingestion_counts_documents_chunks_and_source_types() -> None:
    summary = summarize_ingestion(SAMPLE_DATASET)

    assert summary["document_count"] == 20
    assert summary["chunk_count"] == 20
    assert summary["source_types"]["ticket"] == 6
    assert summary["source_types"]["runbook"] == 4
    assert summary["source_types"]["policy"] == 4


def test_validate_document_rejects_missing_required_fields() -> None:
    with pytest.raises(ValueError, match="Missing required fields"):
        validate_document({"document_id": "bad-doc"})


def test_validate_document_rejects_non_list_tags() -> None:
    document = {
        "document_id": "bad-doc",
        "title": "Bad Doc",
        "category": "test",
        "department": "test",
        "source_type": "ticket",
        "created_at": "2026-01-01",
        "version": "1.0",
        "access_level": "internal",
        "tags": "vpn",
        "content": "Non-empty content",
    }

    with pytest.raises(ValueError, match="tags"):
        validate_document(document)


def test_iter_chunk_records_can_include_embeddings() -> None:
    records = iter_chunk_records(SAMPLE_DATASET, include_embeddings=True)

    assert records
    assert records[0]["embedding_model"] == "hashing-384-v1"
    assert len(records[0]["embedding"]) == 384


def test_export_processed_chunks_writes_jsonl(tmp_path: Path) -> None:
    output_path = tmp_path / "chunks.jsonl"

    result = export_processed_chunks(SAMPLE_DATASET, output_path, include_embeddings=False)

    assert result["chunk_count"] == 20
    assert output_path.exists()
    assert len(output_path.read_text(encoding="utf-8").splitlines()) == 20
