from dataclasses import dataclass
from pathlib import Path

from ingestion.loaders.jsonl_loader import load_jsonl


DEFAULT_CORPUS_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "synthetic" / "enterprise_knowledge_base.jsonl"
)

# Deliberately unrelated to anything in the synthetic corpus, to exercise the
# "I do not know" path -- project_plan.md calls for a slice of unanswerable questions
# in every evaluation set.
UNANSWERABLE_QUESTIONS = [
    "Where is the cafeteria coffee machine?",
    "What is the office WiFi password for guests?",
    "Who won the company's annual chess tournament?",
    "What color is the CEO's car?",
    "When is the next company holiday party?",
]


@dataclass(frozen=True)
class EvaluationQuestion:
    question: str
    expected_document_ids: list[str]
    should_answer: bool
    source_document_id: str | None = None


def build_evaluation_questions(
    corpus_path: Path = DEFAULT_CORPUS_PATH,
    max_questions_per_document: int = 1,
    limit: int | None = 40,
) -> list[EvaluationQuestion]:
    """Build an evaluation set from the synthetic corpus's own expected_questions field.

    Each document already declares questions it should be able to answer (per the
    synthetic data generation schema in project_plan.md), so the document itself is the
    expected retrieval hit -- no separately-authored eval question bank is needed for a
    basic hit-rate/precision/recall pass. A fixed small set of unrelated questions is
    appended to exercise the "I do not know" path.
    """
    questions: list[EvaluationQuestion] = []
    for document in load_jsonl(corpus_path):
        for question in document.get("expected_questions", [])[:max_questions_per_document]:
            questions.append(
                EvaluationQuestion(
                    question=question,
                    expected_document_ids=[document["document_id"]],
                    should_answer=True,
                    source_document_id=document["document_id"],
                )
            )
        if limit is not None and len(questions) >= limit:
            questions = questions[:limit]
            break

    questions.extend(
        EvaluationQuestion(question=question, expected_document_ids=[], should_answer=False)
        for question in UNANSWERABLE_QUESTIONS
    )
    return questions
