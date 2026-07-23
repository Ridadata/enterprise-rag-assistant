from pathlib import Path

from evaluation.dataset import UNANSWERABLE_QUESTIONS, build_evaluation_questions
from evaluation.metrics import (
    expected_source_hit,
    is_idk_response,
    mean,
    percentile,
    precision_at_k,
    recall_at_k,
)
from evaluation.run_evaluation import run_experiment


SAMPLE_DATASET = Path("data/synthetic/sample_documents.jsonl")


def test_expected_source_hit_true_when_any_expected_document_retrieved() -> None:
    assert expected_source_hit(["doc-a", "doc-b"], ["doc-b"]) is True
    assert expected_source_hit(["doc-a"], ["doc-b"]) is False
    assert expected_source_hit([], ["doc-b"]) is False
    assert expected_source_hit(["doc-a"], []) is False


def test_precision_at_k_divides_hits_by_retrieved_count() -> None:
    assert precision_at_k(["doc-a", "doc-b", "doc-c"], ["doc-a"]) == 1 / 3
    assert precision_at_k([], ["doc-a"]) == 0.0


def test_recall_at_k_divides_hits_by_expected_count() -> None:
    assert recall_at_k(["doc-a"], ["doc-a", "doc-b"]) == 0.5
    assert recall_at_k(["doc-a"], []) == 0.0


def test_is_idk_response_matches_the_canonical_idk_string() -> None:
    assert is_idk_response("I do not know based on the available documents.")
    assert not is_idk_response("Based on the retrieved sources: do this.")


def test_mean_and_percentile_handle_empty_input() -> None:
    assert mean([]) == 0.0
    assert percentile([], 0.95) == 0.0
    assert mean([1.0, 2.0, 3.0]) == 2.0
    assert percentile([1.0, 2.0, 3.0, 4.0], 0.95) == 4.0


def test_build_evaluation_questions_reuses_expected_questions_from_corpus() -> None:
    questions = build_evaluation_questions(SAMPLE_DATASET, max_questions_per_document=1, limit=None)

    answerable = [q for q in questions if q.should_answer]
    unanswerable = [q for q in questions if not q.should_answer]

    assert len(answerable) == 20  # one question per document in the 20-document sample set
    assert all(len(q.expected_document_ids) == 1 for q in answerable)
    assert len(unanswerable) == len(UNANSWERABLE_QUESTIONS)
    assert all(q.expected_document_ids == [] for q in unanswerable)


def test_build_evaluation_questions_respects_limit() -> None:
    questions = build_evaluation_questions(SAMPLE_DATASET, limit=5)

    answerable = [q for q in questions if q.should_answer]
    assert len(answerable) == 5


def test_run_experiment_on_local_backend_scores_above_zero_on_hit_rate() -> None:
    questions = build_evaluation_questions(SAMPLE_DATASET, max_questions_per_document=1, limit=10)

    summary = run_experiment(questions, backend="local", top_k=5)

    assert summary["backend"] == "local"
    assert summary["question_count"] == 10 + len(UNANSWERABLE_QUESTIONS)
    assert summary["expected_source_hit_rate"] > 0.0
    assert 0.0 <= summary["idk_correctness_rate"] <= 1.0
    assert summary["mean_latency_ms"] >= 0.0


def test_run_experiment_gracefully_degrades_when_postgres_is_unreachable(monkeypatch) -> None:
    # Port 1 is deterministically unreachable regardless of what's actually running on
    # the machine (unlike relying on "no DB happens to be up" as ambient state).
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://rag_user:rag_password@localhost:1/enterprise_rag")
    questions = build_evaluation_questions(SAMPLE_DATASET, max_questions_per_document=1, limit=3)

    summary = run_experiment(questions, backend="postgres", top_k=5)

    # Every question should fail over to an empty retrieval result (and therefore an
    # "I do not know" answer) without raising.
    assert summary["backend"] == "postgres"
    assert summary["expected_source_hit_rate"] == 0.0
