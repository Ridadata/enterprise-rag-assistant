import logging
from typing import Any

from database.settings import get_psycopg_dsn, get_settings
from ingestion.embedding.provider import get_embedding_provider
from retrieval.vector_search import ALLOWED_FILTER_KEYS, RetrievedChunk


logger = logging.getLogger(__name__)

# "tags" is handled separately below via the array-overlap operator, not a plain column match.
ALLOWED_FILTERS = ALLOWED_FILTER_KEYS - {"tags"}


def _import_psycopg():
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("Install psycopg first: python -m pip install 'psycopg[binary]'") from exc
    return psycopg


def _build_filter_sql(filters: dict[str, str | list[str]] | None) -> tuple[str, list[Any]]:
    if not filters:
        return "", []

    clauses: list[str] = []
    params: list[Any] = []
    for key, value in filters.items():
        values = value if isinstance(value, list) else [value]
        if key == "tags":
            clauses.append("d.tags && %s::text[]")
            params.append(values)
        elif key in ALLOWED_FILTERS:
            clauses.append(f"d.{key} = ANY(%s)")
            params.append(values)

    if not clauses:
        return "", []
    return " AND " + " AND ".join(clauses), params


def retrieve_postgres_chunks(
    question: str,
    filters: dict[str, str | list[str]] | None = None,
    top_k: int = 5,
    min_score: float | None = None,
    database_url: str | None = None,
    embedding_provider: str | None = None,
) -> list[RetrievedChunk]:
    psycopg = _import_psycopg()
    database_url = database_url or get_psycopg_dsn()
    min_score = min_score if min_score is not None else get_settings().min_retrieval_score
    filter_sql, filter_params = _build_filter_sql(filters)

    chunks: list[RetrievedChunk] = []
    try:
        # Connect before computing the query embedding: if postgres is unreachable
        # (e.g. no DB in a dev/test environment), fail fast on the cheap network call
        # instead of paying for a real embedding-model load/download that's about to
        # be thrown away when the caller falls back to local search.
        with psycopg.connect(database_url, connect_timeout=2) as connection:
            provider = get_embedding_provider(embedding_provider)
            query_embedding = provider.vector_to_pgvector(provider.embed_text(question))

            # hybrid_score is computed once in the inner query and filtered on *before*
            # LIMIT, so min_score can't cause a query to return fewer/worse rows than
            # top_k allows.
            sql = f"""
                SELECT chunk_id, document_id, title, source_type, content, chunk_index, hybrid_score
                FROM (
                    SELECT
                        c.chunk_id,
                        d.document_id,
                        d.title,
                        d.source_type,
                        c.content,
                        c.chunk_index,
                        (
                            0.75 * ((1 - (e.embedding <=> %s::vector)) + 1) / 2
                            + 0.25 * LEAST(ts_rank_cd(c.search_vector, plainto_tsquery('english', %s)), 1.0)
                        ) AS hybrid_score
                    FROM embeddings e
                    JOIN chunks c ON c.chunk_id = e.chunk_id
                    JOIN documents d ON d.document_id = c.document_id
                    WHERE e.model_name = %s
                    {filter_sql}
                ) scored
                WHERE hybrid_score >= %s
                ORDER BY hybrid_score DESC
                LIMIT %s
            """
            params = [
                query_embedding,
                question,
                provider.model_name,
                *filter_params,
                min_score,
                top_k,
            ]

            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                for (
                    chunk_id,
                    document_id,
                    title,
                    source_type,
                    content,
                    chunk_index,
                    hybrid_score,
                ) in cursor.fetchall():
                    chunks.append(
                        RetrievedChunk(
                            chunk_id=chunk_id,
                            document_id=document_id,
                            title=title,
                            content=content,
                            score=round(float(hybrid_score), 4),
                            source_type=source_type,
                            chunk_index=chunk_index,
                        )
                    )
    except Exception:
        logger.exception("Postgres hybrid retrieval failed for question=%r", question)
        raise
    return chunks
