from pathlib import Path

import pytest

from ingestion.pipelines.ingest_jsonl import summarize_ingestion, validate_document


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

