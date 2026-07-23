from api.schemas.corpus import CorpusSummary
from database.settings import get_psycopg_dsn


class CorpusUnavailable(RuntimeError):
    """Raised when the corpus summary can't be read from Postgres (e.g. it's unreachable)."""


def get_corpus_summary(database_url: str | None = None) -> CorpusSummary:
    """Corpus counts read from Postgres -- the source of truth once documents are
    ingested, rather than re-parsing a local JSONL file (which may not reflect what's
    actually been loaded, or exist at all in a deployed environment)."""
    try:
        import psycopg
    except ImportError as exc:
        raise CorpusUnavailable("Install psycopg first: python -m pip install 'psycopg[binary]'") from exc

    try:
        with psycopg.connect(database_url or get_psycopg_dsn(), connect_timeout=2) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM documents")
                document_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM chunks")
                chunk_count = cursor.fetchone()[0]

                cursor.execute(
                    "SELECT source_type, COUNT(*) FROM documents GROUP BY source_type"
                )
                source_types = dict(cursor.fetchall())
    except Exception as exc:
        raise CorpusUnavailable(f"Corpus summary unavailable: {exc}") from exc

    return CorpusSummary(
        document_count=document_count,
        chunk_count=chunk_count,
        source_types=source_types,
    )
