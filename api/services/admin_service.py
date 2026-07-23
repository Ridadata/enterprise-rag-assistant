from api.schemas.admin import AdminSummary, CitedDocument, IngestionStatusCount, QueryVolumePoint
from database.settings import get_settings
from monitoring.analytics import get_admin_summary as _get_admin_summary


class AdminSummaryUnavailable(RuntimeError):
    """Raised when the admin summary can't be read from Postgres (e.g. it's unreachable)."""


def get_admin_summary(database_url: str | None = None) -> AdminSummary:
    try:
        summary = _get_admin_summary(database_url=database_url)
    except Exception as exc:
        raise AdminSummaryUnavailable(f"Admin summary unavailable: {exc}") from exc

    return AdminSummary(
        # A config read, not DB-derived, but included here (rather than the UI reading
        # database.settings directly) so the Next.js app never needs backend-internal
        # imports -- it only ever talks to this HTTP API.
        retrieval_backend=get_settings().rag_retrieval_backend,
        total_queries=summary.total_queries,
        mean_latency_ms=summary.mean_latency_ms,
        p95_latency_ms=summary.p95_latency_ms,
        confidence_counts=summary.confidence_counts,
        idk_rate=summary.idk_rate,
        total_tokens_in=summary.total_tokens_in,
        total_tokens_out=summary.total_tokens_out,
        total_cost_estimate=summary.total_cost_estimate,
        queries_by_day=[
            QueryVolumePoint(day=point.day, query_count=point.query_count)
            for point in summary.queries_by_day
        ],
        most_cited_documents=[
            CitedDocument(
                document_id=doc.document_id, title=doc.title, citation_count=doc.citation_count
            )
            for doc in summary.most_cited_documents
        ],
        never_retrieved_document_count=summary.never_retrieved_document_count,
        ingestion_status_counts=[
            IngestionStatusCount(status=item.status, count=item.count)
            for item in summary.ingestion_status_counts
        ],
        most_recent_ingestion_at=summary.most_recent_ingestion_at,
    )
