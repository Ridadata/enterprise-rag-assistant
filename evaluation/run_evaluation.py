import argparse
import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from evaluation.dataset import DEFAULT_CORPUS_PATH, EvaluationQuestion, build_evaluation_questions
from evaluation.metrics import (
    expected_source_hit,
    is_idk_response,
    mean,
    percentile,
    precision_at_k,
    recall_at_k,
)
from generation.answer_generator import generate_grounded_answer
from retrieval.vector_search import RetrievalBackendUnavailable, RetrievedChunk, retrieve_relevant_chunks


@dataclass(frozen=True)
class QuestionResult:
    question: str
    should_answer: bool
    expected_document_ids: list[str]
    retrieved_document_ids: list[str]
    hit: bool
    precision: float
    recall: float
    idk_correct: bool
    latency_ms: float


def _evaluate_question(eq: EvaluationQuestion, top_k: int) -> QuestionResult:
    start = time.perf_counter()
    try:
        chunks: list[RetrievedChunk] = retrieve_relevant_chunks(eq.question, top_k=top_k)
    except RetrievalBackendUnavailable:
        chunks = []
    response, _usage = generate_grounded_answer(eq.question, chunks)
    latency_ms = (time.perf_counter() - start) * 1000

    retrieved_document_ids = [chunk.document_id for chunk in chunks]
    idk = is_idk_response(response.answer)

    return QuestionResult(
        question=eq.question,
        should_answer=eq.should_answer,
        expected_document_ids=eq.expected_document_ids,
        retrieved_document_ids=retrieved_document_ids,
        hit=expected_source_hit(retrieved_document_ids, eq.expected_document_ids)
        if eq.should_answer
        else True,
        precision=precision_at_k(retrieved_document_ids, eq.expected_document_ids)
        if eq.should_answer
        else 0.0,
        recall=recall_at_k(retrieved_document_ids, eq.expected_document_ids) if eq.should_answer else 0.0,
        idk_correct=idk != eq.should_answer,
        latency_ms=latency_ms,
    )


def run_experiment(
    questions: list[EvaluationQuestion], backend: str, top_k: int = 5
) -> dict:
    """Run every question through retrieval + generation with RAG_RETRIEVAL_BACKEND pinned
    to `backend`, and summarize the results. Postgres questions gracefully degrade to
    "no chunks retrieved" (rather than raising) if the DB isn't reachable, so the report
    stays usable even before ingestion has run against a live Postgres instance."""
    previous_backend = os.environ.get("RAG_RETRIEVAL_BACKEND")
    os.environ["RAG_RETRIEVAL_BACKEND"] = backend
    try:
        results = [_evaluate_question(eq, top_k=top_k) for eq in questions]
    finally:
        if previous_backend is None:
            os.environ.pop("RAG_RETRIEVAL_BACKEND", None)
        else:
            os.environ["RAG_RETRIEVAL_BACKEND"] = previous_backend

    answerable = [r for r in results if r.should_answer]
    latencies = [r.latency_ms for r in results]

    return {
        "backend": backend,
        "question_count": len(results),
        "answerable_question_count": len(answerable),
        "unanswerable_question_count": len(results) - len(answerable),
        "expected_source_hit_rate": mean([1.0 if r.hit else 0.0 for r in answerable]),
        "mean_precision_at_k": mean([r.precision for r in answerable]),
        "mean_recall_at_k": mean([r.recall for r in answerable]),
        "idk_correctness_rate": mean([1.0 if r.idk_correct else 0.0 for r in results]),
        "mean_latency_ms": round(mean(latencies), 2),
        "p95_latency_ms": percentile(latencies, 0.95),
        "results": [asdict(r) for r in results],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the basic RAG evaluation harness.")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS_PATH)
    parser.add_argument("--limit", type=int, default=40, help="Max answerable questions to evaluate.")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--backend",
        choices=["local", "postgres", "both"],
        default="both",
        help="Which retrieval backend(s) to evaluate; 'both' compares local vs postgres hybrid.",
    )
    parser.add_argument("--verbose", action="store_true", help="Include per-question results.")
    args = parser.parse_args()

    questions = build_evaluation_questions(args.corpus, limit=args.limit)
    backends = ["local", "postgres"] if args.backend == "both" else [args.backend]

    summaries = [run_experiment(questions, backend=backend, top_k=args.top_k) for backend in backends]
    if not args.verbose:
        for summary in summaries:
            summary.pop("results")

    print(json.dumps(summaries, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
