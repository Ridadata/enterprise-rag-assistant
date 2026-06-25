import re
from dataclasses import dataclass
from pathlib import Path

from ingestion.chunking.simple_chunker import chunk_text
from ingestion.loaders.jsonl_loader import load_jsonl
from ingestion.pipelines.ingest_jsonl import validate_document


DEFAULT_DOCUMENT_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "synthetic" / "sample_documents.jsonl"
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


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    title: str
    content: str
    score: float


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


def retrieve_relevant_chunks(
    question: str,
    filters: dict[str, str | list[str]] | None = None,
    top_k: int = 5,
    document_path: Path = DEFAULT_DOCUMENT_PATH,
    min_score: float = 0.3,
) -> list[RetrievedChunk]:
    """Local keyword retrieval used before pgvector-backed vector search is wired."""
    question_terms = _tokens(question)
    candidates: list[RetrievedChunk] = []

    for document in load_jsonl(document_path):
        validate_document(document)
        if not _matches_filters(document, filters):
            continue

        for chunk in chunk_text(document["content"]):
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
                )
            )

    return sorted(candidates, key=lambda chunk: chunk.score, reverse=True)[:top_k]
