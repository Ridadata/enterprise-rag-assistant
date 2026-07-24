from api.schemas.qa import ConversationTurn
from generation import answer_generator
from generation.answer_generator import (
    _extract_follow_ups,
    build_grounded_answer,
    generate_grounded_answer,
)
from retrieval.vector_search import RetrievedChunk


def _chunk(score: float, content: str = "Some retrieved content.") -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="doc-1::0",
        document_id="doc-1",
        title="Doc",
        content=content,
        score=score,
        source_type="ticket",
    )


def test_troubleshooting_question_prefers_resolution_sentences() -> None:
    chunks = [
        RetrievedChunk(
            chunk_id="ticket-1::0",
            document_id="ticket-1",
            title="Docker Build Ticket",
            content=(
                "Ticket summary: Docker build fails with 401. "
                "Root cause: the registry token expired. "
                "Resolution: update the CI package registry secret and rerun the build."
            ),
            score=0.9,
            source_type="ticket",
        )
    ]

    response = build_grounded_answer("How do I fix Docker build 401?", chunks)

    assert "Resolution: update the CI package registry secret" in response.answer


def test_build_grounded_answer_returns_i_do_not_know_when_no_chunks() -> None:
    response = build_grounded_answer("What is the cafeteria menu?", [])

    assert response.answer == "I do not know based on the available documents."
    assert response.confidence == "low"
    assert response.sources == []
    assert response.model_name == "n/a"
    assert response.latency_ms == 0  # only api/services/rag_service.py fills this in


def test_generate_grounded_answer_reports_zero_cost_usage_for_idk_path() -> None:
    _response, usage = generate_grounded_answer("What is the cafeteria menu?", [])

    assert usage.model_name == "n/a"
    assert usage.tokens_in == 0
    assert usage.tokens_out == 0
    assert usage.cost_estimate == 0.0


def test_confidence_is_high_at_or_above_0_6() -> None:
    response = build_grounded_answer("question", [_chunk(0.6)])
    assert response.confidence == "high"


def test_confidence_is_medium_between_0_5_and_0_6() -> None:
    response = build_grounded_answer("question", [_chunk(0.5)])
    assert response.confidence == "medium"

    response = build_grounded_answer("question", [_chunk(0.59)])
    assert response.confidence == "medium"


def test_confidence_is_low_below_0_5() -> None:
    # Not reachable via normal retrieval (which already filters below MIN_RETRIEVAL_SCORE),
    # but build_grounded_answer() shouldn't assume that invariant holds for every caller.
    response = build_grounded_answer("question", [_chunk(0.49)])
    assert response.confidence == "low"


def test_generate_grounded_answer_uses_mock_provider_by_default() -> None:
    response, usage = generate_grounded_answer("question", [_chunk(0.8, "Grounded evidence text.")])

    assert usage.model_name == "mock-grounded-answer"
    assert usage.cost_estimate == 0.0
    assert usage.tokens_in and usage.tokens_out
    assert "Grounded evidence text." in response.answer
    assert response.model_name == "mock-grounded-answer"


def test_mock_fallback_path_never_reports_follow_up_questions() -> None:
    # The mock/extractive fallback has no real model output to draw follow-ups from --
    # a FOLLOW_UP_QUESTIONS-shaped string in the extractive text itself must not be
    # parsed as if a real model produced it.
    response, _usage = generate_grounded_answer("question", [_chunk(0.8, "Some evidence.")])

    assert response.follow_up_questions == []


def test_extract_follow_ups_parses_marker_and_strips_it_from_answer() -> None:
    raw = (
        "The VPN issue is caused by a stale profile.\n\n"
        'FOLLOW_UP_QUESTIONS: ["How do I refresh the VPN profile?", "Who owns escalation?"]'
    )

    answer, follow_ups = _extract_follow_ups(raw)

    assert answer == "The VPN issue is caused by a stale profile."
    assert follow_ups == ["How do I refresh the VPN profile?", "Who owns escalation?"]


def test_extract_follow_ups_tolerates_single_quoted_list() -> None:
    raw = "Direct answer here.\nFOLLOW_UP_QUESTIONS: ['Question one?', 'Question two?']"

    answer, follow_ups = _extract_follow_ups(raw)

    assert answer == "Direct answer here."
    assert follow_ups == ["Question one?", "Question two?"]


def test_extract_follow_ups_caps_at_three() -> None:
    raw = 'Answer.\nFOLLOW_UP_QUESTIONS: ["one", "two", "three", "four"]'

    _answer, follow_ups = _extract_follow_ups(raw)

    assert follow_ups == ["one", "two", "three"]


def test_extract_follow_ups_returns_empty_when_marker_missing() -> None:
    answer, follow_ups = _extract_follow_ups("Just a plain answer with no marker.")

    assert answer == "Just a plain answer with no marker."
    assert follow_ups == []


def test_extract_follow_ups_returns_answer_unchanged_when_marker_unparsable() -> None:
    raw = "Answer text.\nFOLLOW_UP_QUESTIONS: [not valid json"

    answer, follow_ups = _extract_follow_ups(raw)

    assert answer == raw.strip()
    assert follow_ups == []


def test_generate_grounded_answer_includes_history_in_prompt(monkeypatch) -> None:
    captured: dict = {}

    def fake_generate(system_prompt, user_prompt, *, fallback_text, **kwargs):
        captured["user_prompt"] = user_prompt
        del system_prompt, fallback_text, kwargs

        class _Result:
            text = "An answer."
            model_name = "fake-model"
            tokens_in = 1
            tokens_out = 1
            cost_estimate = None
            is_extractive_fallback = False

        return _Result()

    monkeypatch.setattr(answer_generator, "llm_generate", fake_generate)

    history = [ConversationTurn(question="What is the VPN policy?", answer="MFA is required.")]
    generate_grounded_answer("Is there an exception process?", [_chunk(0.8)], history=history)

    assert "What is the VPN policy?" in captured["user_prompt"]
    assert "MFA is required." in captured["user_prompt"]


def test_generate_grounded_answer_omits_history_block_when_no_history(monkeypatch) -> None:
    captured: dict = {}

    def fake_generate(system_prompt, user_prompt, *, fallback_text, **kwargs):
        captured["user_prompt"] = user_prompt
        del system_prompt, fallback_text, kwargs

        class _Result:
            text = "An answer."
            model_name = "fake-model"
            tokens_in = 1
            tokens_out = 1
            cost_estimate = None
            is_extractive_fallback = False

        return _Result()

    monkeypatch.setattr(answer_generator, "llm_generate", fake_generate)

    generate_grounded_answer("A standalone question", [_chunk(0.8)], history=[])

    assert "Prior conversation" not in captured["user_prompt"]
