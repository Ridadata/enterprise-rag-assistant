import re

from api.schemas.qa import AskResponse
from generation.citation_builder import citations_from_chunks
from retrieval.vector_search import RetrievedChunk


def _extract_relevant_sentences(question: str, chunks: list[RetrievedChunk]) -> list[str]:
    question_terms = set(re.findall(r"[a-z0-9]+", question.lower()))
    selected: list[str] = []

    for chunk in chunks[:3]:
        sentences = re.split(r"(?<=[.!?])\s+", chunk.content.strip())
        ranked_sentences = sorted(
            sentences,
            key=lambda sentence: len(question_terms.intersection(sentence.lower().split())),
            reverse=True,
        )
        for sentence in ranked_sentences:
            clean_sentence = sentence.strip()
            if clean_sentence and clean_sentence not in selected:
                selected.append(clean_sentence)
                break

    return selected


def _confidence_from_chunks(chunks: list[RetrievedChunk]) -> str:
    best_score = chunks[0].score if chunks else 0.0
    if best_score >= 0.7:
        return "high"
    if best_score >= 0.35:
        return "medium"
    return "low"


def build_grounded_answer(question: str, chunks: list[RetrievedChunk]) -> AskResponse:
    if not chunks:
        return AskResponse(
            answer="I do not know based on the available documents.",
            confidence="low",
            limitations="No retrieved source passed the minimum evidence threshold.",
            next_step="Add relevant documents or broaden the search filters, then ask again.",
            sources=[],
        )

    relevant_sentences = _extract_relevant_sentences(question, chunks)
    evidence = " ".join(relevant_sentences) if relevant_sentences else chunks[0].content

    return AskResponse(
        answer=f"Based on the retrieved sources: {evidence}",
        confidence=_confidence_from_chunks(chunks),
        limitations=(
            "This MVP answer is extractive and uses local keyword retrieval until "
            "pgvector embeddings and the grounded LLM generator are connected."
        ),
        next_step="Review the cited source chunks, then wire pgvector retrieval as the next backend step.",
        sources=citations_from_chunks(chunks),
    )
