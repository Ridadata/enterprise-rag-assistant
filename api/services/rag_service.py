import logging
import time

from api.schemas.qa import AskRequest, AskResponse
from database.settings import get_psycopg_dsn
from generation.answer_generator import GenerationUsage, generate_grounded_answer
from retrieval.vector_search import RetrievedChunk, retrieve_relevant_chunks


logger = logging.getLogger(__name__)


def _log_query_and_answer(
    request: AskRequest,
    chunks: list[RetrievedChunk],
    response: AskResponse,
    usage: GenerationUsage,
    latency_ms: int,
) -> None:
    """Best-effort query/answer/retrieved-context logging to Postgres.

    Never raises: a logging failure must not break answering a question. Individual
    retrieved_contexts rows use a savepoint so one chunk_id that hasn't been ingested
    into Postgres (e.g. while running on the local keyword-search fallback) doesn't
    abort logging of the query/answer rows themselves.
    """
    try:
        import psycopg
        from psycopg.types.json import Jsonb
    except ImportError:
        logger.debug("psycopg not installed; skipping query/answer logging.")
        return

    try:
        with psycopg.connect(get_psycopg_dsn(), connect_timeout=2) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO queries (user_id, question, filters_json, latency_ms, status)
                    VALUES (%s, %s, %s, %s, 'completed')
                    RETURNING query_id
                    """,
                    (request.user_id, request.question, Jsonb(request.filters), latency_ms),
                )
                query_id = cursor.fetchone()[0]

                for rank, chunk in enumerate(chunks, start=1):
                    try:
                        with connection.transaction():
                            cursor.execute(
                                """
                                INSERT INTO retrieved_contexts (query_id, chunk_id, rank, hybrid_score)
                                VALUES (%s, %s, %s, %s)
                                ON CONFLICT (query_id, chunk_id) DO NOTHING
                                """,
                                (query_id, chunk.chunk_id, rank, chunk.score),
                            )
                    except Exception:
                        logger.debug(
                            "Skipping retrieved_contexts row for chunk_id=%r "
                            "(not ingested into postgres?)",
                            chunk.chunk_id,
                        )

                cursor.execute(
                    """
                    INSERT INTO answers (
                        query_id, answer_text, confidence, limitations,
                        model_name, prompt_version, tokens_in, tokens_out, cost_estimate
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        query_id,
                        response.answer,
                        response.confidence,
                        response.limitations,
                        usage.model_name,
                        usage.prompt_version,
                        usage.tokens_in,
                        usage.tokens_out,
                        usage.cost_estimate,
                    ),
                )
    except Exception:
        logger.exception("Failed to log query/answer to Postgres; continuing without logging.")


def answer_question(request: AskRequest) -> AskResponse:
    start = time.perf_counter()
    chunks = retrieve_relevant_chunks(request.question, filters=request.filters)
    response, usage = generate_grounded_answer(question=request.question, chunks=chunks)
    latency_ms = int((time.perf_counter() - start) * 1000)

    _log_query_and_answer(request, chunks, response, usage, latency_ms)

    return response.model_copy(update={"latency_ms": latency_ms})
