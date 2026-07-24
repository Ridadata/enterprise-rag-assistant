from dataclasses import dataclass

from api.schemas.qa import ConversationTurn
from database.settings import get_settings
from generation.llm_client import generate as llm_generate
from generation.prompts import load_system_prompt


@dataclass(frozen=True)
class RewriteResult:
    query: str
    was_rewritten: bool


# Observed in practice: an LLM told "only rewrite if it depends on history, otherwise
# return it unchanged" will still over-eagerly graft history onto a question that's
# already standalone -- e.g. "What is the password reset policy?" asked right after a
# Kubernetes conversation came back rewritten as "...in the Kubernetes environment that
# experienced the pod crash loop...", which then retrieved Kubernetes docs instead of the
# actual password policy. Gating the LLM call on a cheap, deterministic check for
# ellipsis/reference markers (rather than trusting the model's own judgment on every
# question) means a self-contained new question never reaches the rewriter at all, so it
# can't be contaminated by unrelated prior turns.
_REFERENCE_MARKERS = (
    " it", " it?", " it.", "it's", "its ", " that", " this", " these", " those",
    " they", " them", " their", "the other", "the previous", "the above",
    "the first one", "the second one", "the last one", " again", "instead",
    "what about", "how about", "and the", "also,",
)
_MAX_STANDALONE_WORD_COUNT = 5


def _looks_like_a_followup(question: str) -> bool:
    """A cheap pre-filter for "does this question depend on what came before", so the
    rewriter only invokes an LLM (and only risks contaminating retrieval) when there's an
    actual signal that it's needed."""
    lowered = f" {question.strip().lower()} "
    if len(lowered.split()) <= _MAX_STANDALONE_WORD_COUNT:
        # Short questions ("How was it mitigated?", "Why did that happen?") are
        # frequently elliptical even when they don't contain an obvious pronoun.
        return True
    return any(marker in lowered for marker in _REFERENCE_MARKERS)


def _format_history(history: list[ConversationTurn], max_turns: int) -> str:
    recent = history[-max_turns:] if max_turns > 0 else history
    lines: list[str] = []
    for turn in recent:
        lines.append(f"User: {turn.question}")
        lines.append(f"Assistant: {turn.answer}")
    return "\n".join(lines)


def rewrite_query(question: str, history: list[ConversationTurn]) -> RewriteResult:
    """Condenses `question` (a possible follow-up) plus `history` into a standalone
    query for retrieval, so e.g. "is there a workaround" after a VPN question retrieves
    VPN documents rather than whatever "workaround" alone happens to match.

    A no-op (returns `question` unchanged, `was_rewritten=False`) when there's no history
    to rewrite against, rewriting is disabled, the question doesn't look like it depends
    on prior turns at all (see _looks_like_a_followup), or the call falls all the way back
    to the deterministic mock provider (i.e. no real LLM actually rewrote anything) --
    retrieval always gets *something* usable, it just isn't history-aware in that case.
    See database/settings.py's query_rewrite_* fields for why this call uses a tighter
    retry/timeout budget than the main answer-generation call.
    """
    settings = get_settings()
    if not history or not settings.query_rewrite_enabled or not _looks_like_a_followup(question):
        return RewriteResult(query=question, was_rewritten=False)

    system_prompt = load_system_prompt("query_rewrite_prompt")
    history_text = _format_history(history, settings.max_history_turns)
    user_prompt = (
        f"Conversation so far:\n{history_text}\n\n"
        f"Follow-up question: {question}\n\n"
        "Standalone question:"
    )

    result = llm_generate(
        system_prompt,
        user_prompt,
        fallback_text=question,
        max_retries=settings.query_rewrite_max_retries,
        timeout_seconds=settings.query_rewrite_timeout_seconds,
    )

    if result.is_extractive_fallback:
        return RewriteResult(query=question, was_rewritten=False)

    rewritten = result.text.strip().strip('"')
    if not rewritten:
        return RewriteResult(query=question, was_rewritten=False)

    return RewriteResult(query=rewritten, was_rewritten=True)
