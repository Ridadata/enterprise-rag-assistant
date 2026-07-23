from generation.answer_generator import build_grounded_answer, generate_grounded_answer
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
