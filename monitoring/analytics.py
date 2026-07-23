from dataclasses import dataclass
from datetime import date, datetime

from database.settings import get_psycopg_dsn
from evaluation.metrics import is_idk_response


@dataclass(frozen=True)
class QueryVolumePoint:
    day: date
    query_count: int


@dataclass(frozen=True)
class CitedDocument:
    document_id: str
    title: str
    citation_count: int


@dataclass(frozen=True)
class IngestionStatusCount:
    status: str
    count: int


@dataclass(frozen=True)
class AdminSummary:
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


def _import_psycopg():
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("Install psycopg first: python -m pip install 'psycopg[binary]'") from exc
    return psycopg


def get_admin_summary(database_url: str | None = None, top_cited_limit: int = 10) -> AdminSummary:
    """Usage/quality metrics computed from the queries/answers/retrieved_contexts tables
    that rag_service actually writes to. Sections from project_plan.md's dashboard spec
    that nothing populates yet (feedback, evaluation_results, ingestion error logs) are
    deliberately left out rather than shown as misleadingly-empty placeholders."""
    psycopg = _import_psycopg()
    with psycopg.connect(database_url or get_psycopg_dsn(), connect_timeout=2) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM queries")
            total_queries = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT
                    AVG(latency_ms),
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms)
                FROM queries
                WHERE latency_ms IS NOT NULL
                """
            )
            mean_latency, p95_latency = cursor.fetchone()

            cursor.execute("SELECT confidence, COUNT(*) FROM answers GROUP BY confidence")
            confidence_counts = dict(cursor.fetchall())

            cursor.execute("SELECT answer_text FROM answers")
            answer_texts = [row[0] for row in cursor.fetchall()]
            idk_count = sum(1 for text in answer_texts if is_idk_response(text))
            idk_rate = (idk_count / len(answer_texts)) if answer_texts else 0.0

            cursor.execute(
                """
                SELECT
                    COALESCE(SUM(tokens_in), 0),
                    COALESCE(SUM(tokens_out), 0),
                    COALESCE(SUM(cost_estimate), 0)
                FROM answers
                """
            )
            total_tokens_in, total_tokens_out, total_cost_estimate = cursor.fetchone()

            cursor.execute(
                """
                SELECT created_at::date, COUNT(*)
                FROM queries
                GROUP BY created_at::date
                ORDER BY created_at::date
                """
            )
            queries_by_day = [QueryVolumePoint(day=row[0], query_count=row[1]) for row in cursor.fetchall()]

            cursor.execute(
                """
                SELECT d.document_id, d.title, COUNT(*) AS citations
                FROM retrieved_contexts rc
                JOIN chunks c ON c.chunk_id = rc.chunk_id
                JOIN documents d ON d.document_id = c.document_id
                GROUP BY d.document_id, d.title
                ORDER BY citations DESC
                LIMIT %s
                """,
                (top_cited_limit,),
            )
            most_cited_documents = [
                CitedDocument(document_id=row[0], title=row[1], citation_count=row[2])
                for row in cursor.fetchall()
            ]

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM documents d
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM chunks c
                    JOIN retrieved_contexts rc ON rc.chunk_id = c.chunk_id
                    WHERE c.document_id = d.document_id
                )
                """
            )
            never_retrieved_document_count = cursor.fetchone()[0]

            cursor.execute("SELECT ingestion_status, COUNT(*) FROM documents GROUP BY ingestion_status")
            ingestion_status_counts = [
                IngestionStatusCount(status=row[0], count=row[1]) for row in cursor.fetchall()
            ]

            cursor.execute("SELECT MAX(inserted_at) FROM documents")
            most_recent_ingestion_at = cursor.fetchone()[0]

    return AdminSummary(
        total_queries=total_queries,
        mean_latency_ms=round(float(mean_latency), 2) if mean_latency is not None else None,
        p95_latency_ms=round(float(p95_latency), 2) if p95_latency is not None else None,
        confidence_counts=confidence_counts,
        idk_rate=round(idk_rate, 4),
        total_tokens_in=int(total_tokens_in),
        total_tokens_out=int(total_tokens_out),
        total_cost_estimate=float(total_cost_estimate),
        queries_by_day=queries_by_day,
        most_cited_documents=most_cited_documents,
        never_retrieved_document_count=never_retrieved_document_count,
        ingestion_status_counts=ingestion_status_counts,
        most_recent_ingestion_at=most_recent_ingestion_at,
    )
