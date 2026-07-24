import logging
import re
from dataclasses import dataclass
from pathlib import Path

from database.settings import get_settings
from ingestion.chunking.simple_chunker import chunk_text
from ingestion.loaders.jsonl_loader import load_jsonl
from ingestion.pipelines.ingest_jsonl import validate_document


logger = logging.getLogger(__name__)

# Canonical set of filter keys accepted by any retrieval backend. The API layer
# validates against this so unrecognized keys fail fast with a 422 instead of
# silently matching nothing (local backend) or being ignored (postgres backend).
ALLOWED_FILTER_KEYS = {"category", "department", "source_type", "access_level", "tags"}

DEFAULT_DOCUMENT_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "synthetic" / "enterprise_knowledge_base.jsonl"
)

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "cause",
    "caused",
    "for",
    "from",
    "how",
    "i",
    "incident",
    "in",
    "is",
    "of",
    "on",
    "or",
    "should",
    "the",
    "to",
    "what",
    "when",
    "where",
    "which",
    "with",
}


class RetrievalBackendUnavailable(RuntimeError):
    """Raised when RAG_RETRIEVAL_BACKEND is pinned to "postgres" and it fails (no fallback)."""


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    title: str
    content: str
    score: float
    source_type: str = ""
    # 0-based position of this chunk within its source document.
    chunk_index: int = 0


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if token not in STOP_WORDS}


def _matches_filters(document: dict, filters: dict[str, str | list[str]] | None) -> bool:
    if not filters:
        return True

    for key, expected in filters.items():
        actual = document.get(key)
        expected_values = expected if isinstance(expected, list) else [expected]
        if isinstance(actual, list):
            if not set(expected_values).intersection(actual):
                return False
        elif actual not in expected_values:
            return False
    return True


def _score_chunk(question_terms: set[str], document: dict, content: str) -> float:
    searchable = " ".join(
        [
            document["title"],
            document["category"],
            document["department"],
            document["source_type"],
            " ".join(document.get("tags", [])),
            content,
        ]
    )
    chunk_terms = _tokens(searchable)
    if not question_terms or not chunk_terms:
        return 0.0

    overlap = question_terms.intersection(chunk_terms)
    title_bonus = 0.15 if question_terms.intersection(_tokens(document["title"])) else 0.0
    tag_bonus = 0.10 if question_terms.intersection(_tokens(" ".join(document.get("tags", [])))) else 0.0
    return min((len(overlap) / len(question_terms)) + title_bonus + tag_bonus, 1.0)


def _diversify_chunks(candidates: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
    sorted_candidates = sorted(candidates, key=lambda chunk: chunk.score, reverse=True)
    selected: list[RetrievedChunk] = []
    seen_source_types: set[str] = set()

    for candidate in sorted_candidates:
        if candidate.source_type and candidate.source_type in seen_source_types:
            continue
        selected.append(candidate)
        if candidate.source_type:
            seen_source_types.add(candidate.source_type)
        if len(selected) == top_k:
            return selected

    for candidate in sorted_candidates:
        if candidate not in selected:
            selected.append(candidate)
        if len(selected) == top_k:
            break
    return selected


def retrieve_relevant_chunks(
    question: str,
    filters: dict[str, str | list[str]] | None = None,
    top_k: int = 5,
    document_path: Path = DEFAULT_DOCUMENT_PATH,
    min_score: float | None = None,
) -> list[RetrievedChunk]:
    """Retrieve chunks using the configured backend, with local JSONL as the stable
    fallback, then rerank (see retrieval/reranker.py) if enabled.

    `question` should already be the history-aware, standalone form of a follow-up (see
    generation/query_rewriter.py) -- this function only does first-stage retrieval plus
    reranking, it has no notion of conversation history itself.
    """
    settings = get_settings()
    min_score = min_score if min_score is not None else settings.min_retrieval_score

    # Over-fetch when reranking so it has a real pool to re-sort rather than just
    # confirming the first-stage order.
    fetch_k = max(top_k, settings.rerank_candidate_pool) if settings.rerank_enabled else top_k

    candidates = _retrieve_candidates(
        question,
        filters=filters,
        top_k=fetch_k,
        document_path=document_path,
        min_score=min_score,
    )

    if not settings.rerank_enabled:
        return candidates[:top_k]

    from retrieval.reranker import rerank_chunks

    return rerank_chunks(
        question,
        candidates,
        top_k=top_k,
        model_name=settings.rerank_model,
        min_score=settings.rerank_min_score,
    )


def _retrieve_candidates(
    question: str,
    filters: dict[str, str | list[str]] | None,
    top_k: int,
    document_path: Path,
    min_score: float,
) -> list[RetrievedChunk]:
    backend = get_settings().rag_retrieval_backend.lower()
    if backend in {"postgres", "auto"}:
        try:
            from retrieval.postgres_vector_search import retrieve_postgres_chunks

            return retrieve_postgres_chunks(
                question=question,
                filters=filters,
                top_k=top_k,
                min_score=min_score,
            )
        except Exception as exc:
            if backend == "postgres":
                raise RetrievalBackendUnavailable(
                    f"Postgres retrieval backend failed: {exc}"
                ) from exc
            logger.warning(
                "Postgres retrieval backend failed; falling back to local keyword search.",
                exc_info=True,
            )

    return retrieve_local_chunks(
        question=question,
        filters=filters,
        top_k=top_k,
        document_path=document_path,
        min_score=min_score,
    )


def retrieve_local_chunks(
    question: str,
    filters: dict[str, str | list[str]] | None = None,
    top_k: int = 5,
    document_path: Path = DEFAULT_DOCUMENT_PATH,
    min_score: float | None = None,
) -> list[RetrievedChunk]:
    """Local keyword retrieval backend (fallback when postgres hybrid search is unavailable)."""
    min_score = min_score if min_score is not None else get_settings().min_retrieval_score
    question_terms = _tokens(question)
    candidates: list[RetrievedChunk] = []

    for document in load_jsonl(document_path):
        validate_document(document)
        if not _matches_filters(document, filters):
            continue

        for chunk in chunk_text(document["content"], source_type=document["source_type"]):
            score = _score_chunk(question_terms, document, chunk.content)
            if score < min_score:
                continue
            candidates.append(
                RetrievedChunk(
                    chunk_id=f"{document['document_id']}::{chunk.chunk_index}",
                    document_id=document["document_id"],
                    title=document["title"],
                    content=chunk.content,
                    score=round(score, 4),
                    source_type=document["source_type"],
                    chunk_index=chunk.chunk_index,
                )
            )

    return _diversify_chunks(candidates, top_k)
