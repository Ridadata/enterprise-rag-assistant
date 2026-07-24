import argparse
import json
import logging
from pathlib import Path
from typing import Any

from database.settings import get_psycopg_dsn
from ingestion.embedding.provider import get_embedding_provider
from ingestion.loaders.jsonl_loader import load_jsonl
from ingestion.pipelines.ingest_jsonl import document_checksum, validate_document
from ingestion.chunking.simple_chunker import chunk_text


logger = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "database" / "schema.sql"


def _import_psycopg():
    try:
        import psycopg
        from psycopg.types.json import Jsonb
    except ImportError as exc:
        raise RuntimeError("Install psycopg first: python -m pip install 'psycopg[binary]'") from exc
    return psycopg, Jsonb


def ensure_schema(database_url: str, schema_path: Path = SCHEMA_PATH) -> None:
    psycopg, _ = _import_psycopg()
    schema_sql = schema_path.read_text(encoding="utf-8")
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(schema_sql)


def reset_ingested_data(database_url: str) -> None:
    psycopg, _ = _import_psycopg()
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE documents RESTART IDENTITY CASCADE")


def _existing_document_checksums(cursor) -> dict[str, str]:
    cursor.execute("SELECT document_id, checksum FROM documents")
    return dict(cursor.fetchall())


def _document_ids_with_embeddings(cursor, model_name: str) -> set[str]:
    cursor.execute(
        """
        SELECT DISTINCT c.document_id
        FROM chunks c
        JOIN embeddings e ON e.chunk_id = c.chunk_id
        WHERE e.model_name = %s
        """,
        (model_name,),
    )
    return {document_id for (document_id,) in cursor.fetchall()}


def _upsert_document(cursor, document: dict[str, Any], source_path: Path, checksum: str) -> None:
    cursor.execute(
        """
        INSERT INTO documents (
            document_id, title, category, department, source_type, created_at,
            version, access_level, tags, storage_path, checksum, ingestion_status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ingested')
        ON CONFLICT (document_id) DO UPDATE SET
            title = EXCLUDED.title,
            category = EXCLUDED.category,
            department = EXCLUDED.department,
            source_type = EXCLUDED.source_type,
            created_at = EXCLUDED.created_at,
            version = EXCLUDED.version,
            access_level = EXCLUDED.access_level,
            tags = EXCLUDED.tags,
            storage_path = EXCLUDED.storage_path,
            checksum = EXCLUDED.checksum,
            ingestion_status = 'ingested'
        """,
        (
            document["document_id"],
            document["title"],
            document["category"],
            document["department"],
            document["source_type"],
            document["created_at"],
            document["version"],
            document["access_level"],
            document["tags"],
            str(source_path),
            checksum,
        ),
    )


def _replace_chunks_and_embeddings(cursor, Jsonb, document: dict[str, Any], checksum: str, provider) -> int:
    # Delete-then-reinsert per document: an UPSERT keyed on chunk_id can't detect chunks
    # that no longer exist (e.g. the document's content shrank since the last ingestion
    # run), so stale rows would otherwise persist forever. ON DELETE CASCADE on
    # embeddings/retrieved_contexts cleans those up along with the chunk row.
    cursor.execute("DELETE FROM chunks WHERE document_id = %s", (document["document_id"],))

    chunk_count = 0
    for chunk in chunk_text(document["content"], source_type=document["source_type"]):
        chunk_id = f"{document['document_id']}::{chunk.chunk_index}"
        metadata = {
            "title": document["title"],
            "category": document["category"],
            "department": document["department"],
            "source_type": document["source_type"],
            "created_at": document["created_at"],
            "access_level": document["access_level"],
            "tags": document["tags"],
            "checksum": checksum,
        }
        cursor.execute(
            """
            INSERT INTO chunks (
                chunk_id, document_id, chunk_index, section_title,
                content, token_count, metadata_json
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                chunk_id,
                document["document_id"],
                chunk.chunk_index,
                chunk.section_title,
                chunk.content,
                chunk.token_count,
                Jsonb(metadata),
            ),
        )

        embedding_vector = provider.embed_text(chunk.content)
        if len(embedding_vector) != provider.dimension:
            raise ValueError(
                f"Embedding for chunk {chunk_id!r} has dimension {len(embedding_vector)}, "
                f"expected {provider.dimension} for model {provider.model_name!r}"
            )
        embedding = provider.vector_to_pgvector(embedding_vector)
        cursor.execute(
            """
            INSERT INTO embeddings (chunk_id, model_name, embedding)
            VALUES (%s, %s, %s::vector)
            ON CONFLICT (chunk_id, model_name) DO UPDATE SET
                embedding = EXCLUDED.embedding,
                created_at = now()
            """,
            (chunk_id, provider.model_name, embedding),
        )
        chunk_count += 1

    if chunk_count == 0:
        raise ValueError(f"Document {document['document_id']!r} produced zero chunks")

    return chunk_count


def load_jsonl_to_postgres(
    source_path: Path,
    database_url: str | None = None,
    reset: bool = False,
    embedding_provider: str | None = None,
) -> dict[str, Any]:
    """Ingest a JSONL document set into Postgres.

    Each document is validated, upserted, and committed independently: a single bad or
    duplicate document is logged and skipped rather than aborting (or silently
    corrupting) the whole batch, and documents already committed before a later failure
    stay committed.

    A document is skipped entirely -- no chunking, no embedding, no write of any kind --
    when its content checksum matches what's already stored *and* it already has
    embeddings under the currently configured model, since re-running this script would
    otherwise redo the most expensive work (re-chunking and re-embedding every
    document) unconditionally on every invocation regardless of whether anything
    actually changed. Only new documents, documents whose content changed, or documents
    never embedded under the current model do real work. --reset bypasses this
    naturally: it truncates everything first, so there's nothing left to compare
    against and every document is treated as new.
    """
    database_url = database_url or get_psycopg_dsn()
    provider = get_embedding_provider(embedding_provider)
    psycopg, Jsonb = _import_psycopg()
    ensure_schema(database_url)
    if reset:
        reset_ingested_data(database_url)

    document_count = 0
    chunk_count = 0
    seen_document_ids: set[str] = set()
    duplicate_document_ids: list[str] = []
    unchanged_document_ids: list[str] = []
    failed_documents: list[dict[str, str]] = []

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            existing_checksums = _existing_document_checksums(cursor)
            already_embedded = _document_ids_with_embeddings(cursor, provider.model_name)

        for document in load_jsonl(source_path):
            try:
                validate_document(document)
            except Exception as exc:
                logger.exception("Invalid document; skipping.")
                failed_documents.append({"document_id": document.get("document_id"), "error": str(exc)})
                continue

            document_id = document["document_id"]
            if document_id in seen_document_ids:
                duplicate_document_ids.append(document_id)
                logger.warning(
                    "Duplicate document_id %r in %s; skipping repeat occurrence.",
                    document_id,
                    source_path,
                )
                continue
            seen_document_ids.add(document_id)

            checksum = document_checksum(document)
            if existing_checksums.get(document_id) == checksum and document_id in already_embedded:
                unchanged_document_ids.append(document_id)
                document_count += 1
                continue

            try:
                with connection.cursor() as cursor:
                    _upsert_document(cursor, document, source_path, checksum)
                    chunk_count += _replace_chunks_and_embeddings(cursor, Jsonb, document, checksum, provider)
                connection.commit()
                document_count += 1
            except Exception as exc:
                connection.rollback()
                logger.exception("Failed to ingest document %r; skipping.", document_id)
                failed_documents.append({"document_id": document_id, "error": str(exc)})

    return {
        "database_url": database_url,
        "source_path": str(source_path),
        "document_count": document_count,
        "chunk_count": chunk_count,
        "embedding_model": provider.model_name,
        "duplicate_document_ids": duplicate_document_ids,
        "unchanged_document_ids": unchanged_document_ids,
        "failed_documents": failed_documents,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Load JSONL documents into PostgreSQL + pgvector.")
    parser.add_argument("source_path", type=Path)
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--reset", action="store_true")
    parser.add_argument(
        "--embedding-provider",
        default=None,
        choices=["hash", "sentence_transformers"],
        help="Override EMBEDDING_PROVIDER for this run.",
    )
    args = parser.parse_args()

    result = load_jsonl_to_postgres(
        source_path=args.source_path,
        database_url=args.database_url,
        reset=args.reset,
        embedding_provider=args.embedding_provider,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
