import json
import re
from dataclasses import dataclass

from api.schemas.qa import AskResponse, ConversationTurn
from generation.citation_builder import citations_from_chunks
from generation.llm_client import generate as llm_generate
from generation.prompts import load_system_prompt
from retrieval.vector_search import RetrievedChunk


PROMPT_VERSION = "qa-v2"

_FOLLOW_UP_PATTERN = re.compile(r"FOLLOW_UP_QUESTIONS:\s*(\[.*?\])\s*$", re.DOTALL)

_MAX_HISTORY_TURNS_IN_PROMPT = 6


@dataclass(frozen=True)
class GenerationUsage:
    model_name: str
    prompt_version: str
    tokens_in: int | None
    tokens_out: int | None
    cost_estimate: float | None


def _extract_relevant_sentences(question: str, chunks: list[RetrievedChunk]) -> list[str]:
    question_terms = set(re.findall(r"[a-z0-9]+", question.lower()))
    troubleshooting_terms = {"fix", "resolve", "resolution", "troubleshoot", "recover", "respond"}
    cause_terms = {"cause", "caused", "root"}
    selected: list[str] = []

    for chunk in chunks[:3]:
        sentences = re.split(r"(?<=[.!?])\s+", chunk.content.strip())

        def score_sentence(sentence: str) -> int:
            sentence_terms = set(re.findall(r"[a-z0-9]+", sentence.lower()))
            score = len(question_terms.intersection(sentence_terms))
            if question_terms.intersection(troubleshooting_terms):
                if sentence.lower().startswith(("resolution", "procedure", "validation", "escalation")):
                    score += 5
            if question_terms.intersection(cause_terms) and "root cause" in sentence.lower():
                score += 5
            return score

        ranked_sentences = sorted(
            sentences,
            key=score_sentence,
            reverse=True,
        )
        for sentence in ranked_sentences:
            clean_sentence = sentence.strip()
            if clean_sentence and clean_sentence not in selected:
                selected.append(clean_sentence)
                break

    return selected


def _confidence_from_chunks(chunks: list[RetrievedChunk]) -> str:
    # Retrieval already drops anything below MIN_RETRIEVAL_SCORE (0.5 by default), so a
    # non-empty chunk list is always at least "medium" by construction -- "low" is a
    # defensive floor for callers that pass a lower min_score explicitly (the no-chunks
    # IDK path is hardcoded to "low" separately). Calibrated against measured scores:
    # local keyword backend's relevant matches ~0.58-1.0, postgres hybrid's relevant
    # matches ~0.52-0.67 (see database/settings.py's min_retrieval_score comment) --
    # unlike the local backend, hybrid scores rarely approach 1.0, so "high" is set well
    # below that. When reranking is enabled (the default), chunks[0].score is instead a
    # sigmoid-normalized cross-encoder score -- see retrieval/reranker.py -- which in
    # practice separates similarly at these same cut points for genuinely relevant vs.
    # borderline results.
    best_score = chunks[0].score if chunks else 0.0
    if best_score >= 0.6:
        return "high"
    if best_score >= 0.5:
        return "medium"
    return "low"


def _format_history(history: list[ConversationTurn]) -> str:
    recent = history[-_MAX_HISTORY_TURNS_IN_PROMPT:]
    lines: list[str] = []
    for turn in recent:
        lines.append(f"User: {turn.question}")
        lines.append(f"Assistant: {turn.answer}")
    return "\n".join(lines)


def _build_user_prompt(question: str, chunks: list[RetrievedChunk], history: list[ConversationTurn]) -> str:
    context_blocks = [
        f"[Source {index}] {chunk.title} ({chunk.source_type}, chunk {chunk.chunk_id})\n{chunk.content}"
        for index, chunk in enumerate(chunks, start=1)
    ]
    context = "\n\n".join(context_blocks)
    history_block = f"Prior conversation:\n{_format_history(history)}\n\n" if history else ""
    return (
        f"{history_block}"
        f"Question: {question}\n\n"
        f"Context:\n{context}\n\n"
        "Answer using only the context above and cite sources by their [Source N] label."
    )


def _extract_follow_ups(raw_text: str) -> tuple[str, list[str]]:
    """Splits the model's raw output into (displayed answer, follow-up questions),
    parsing the `FOLLOW_UP_QUESTIONS: [...]` marker the system prompt asks for. Tolerant
    of near-JSON output (e.g. single quotes) since not every provider follows the format
    equally strictly; if the marker is missing or unparsable, the raw text is returned
    unchanged with no follow-ups rather than failing the whole answer over it.
    """
    match = _FOLLOW_UP_PATTERN.search(raw_text)
    if not match:
        return raw_text.strip(), []

    answer_text = raw_text[: match.start()].strip()
    raw_list = match.group(1)
    try:
        parsed = json.loads(raw_list)
    except json.JSONDecodeError:
        try:
            parsed = json.loads(raw_list.replace("'", '"'))
        except json.JSONDecodeError:
            return answer_text, []

    if not isinstance(parsed, list):
        return answer_text, []

    follow_ups = [str(item).strip() for item in parsed if str(item).strip()]
    return answer_text, follow_ups[:3]


def generate_grounded_answer(
    question: str,
    chunks: list[RetrievedChunk],
    history: list[ConversationTurn] | None = None,
) -> tuple[AskResponse, GenerationUsage]:
    history = history or []

    if not chunks:
        response = AskResponse(
            answer="I do not know based on the available documents.",
            confidence="low",
            limitations="No retrieved source passed the minimum evidence threshold.",
            next_step="Add relevant documents or broaden the search filters, then ask again.",
            sources=[],
            model_name="n/a",
        )
        usage = GenerationUsage(
            model_name="n/a",
            prompt_version=PROMPT_VERSION,
            tokens_in=0,
            tokens_out=0,
            cost_estimate=0.0,
        )
        return response, usage

    relevant_sentences = _extract_relevant_sentences(question, chunks)
    fallback_text = " ".join(relevant_sentences) if relevant_sentences else chunks[0].content
    fallback_answer = f"Based on the retrieved sources: {fallback_text}"

    system_prompt = load_system_prompt("qa_system_prompt")
    user_prompt = _build_user_prompt(question, chunks, history)
    llm_result = llm_generate(system_prompt, user_prompt, fallback_text=fallback_answer)

    limitations = (
        "This MVP answer is extractive (mock LLM provider, or a real provider call that "
        "failed and fell back) rather than generated by a model."
        if llm_result.is_extractive_fallback
        else "Answer generated by the configured LLM from retrieved context only."
    )

    answer_text, follow_up_questions = (
        (llm_result.text, []) if llm_result.is_extractive_fallback else _extract_follow_ups(llm_result.text)
    )

    response = AskResponse(
        answer=answer_text,
        confidence=_confidence_from_chunks(chunks),
        limitations=limitations,
        next_step="Review the cited source chunks for full detail.",
        sources=citations_from_chunks(chunks),
        model_name=llm_result.model_name,
        follow_up_questions=follow_up_questions,
    )
    usage = GenerationUsage(
        model_name=llm_result.model_name,
        prompt_version=PROMPT_VERSION,
        tokens_in=llm_result.tokens_in,
        tokens_out=llm_result.tokens_out,
        cost_estimate=llm_result.cost_estimate,
    )
    return response, usage


def build_grounded_answer(question: str, chunks: list[RetrievedChunk]) -> AskResponse:
    """Convenience wrapper around generate_grounded_answer() for callers that don't need usage metadata."""
    response, _usage = generate_grounded_answer(question, chunks)
    return response
