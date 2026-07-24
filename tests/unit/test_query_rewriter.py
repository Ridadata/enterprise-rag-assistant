from api.schemas.qa import ConversationTurn
from generation import query_rewriter
from generation.query_rewriter import rewrite_query


def test_no_history_returns_question_unchanged_without_calling_llm(monkeypatch) -> None:
    def _fail_if_called(*args, **kwargs):
        raise AssertionError("llm_generate should not be called when there's no history")

    monkeypatch.setattr(query_rewriter, "llm_generate", _fail_if_called)

    result = rewrite_query("What systems require MFA?", [])

    assert result.query == "What systems require MFA?"
    assert result.was_rewritten is False


def test_rewrite_disabled_returns_question_unchanged(monkeypatch) -> None:
    monkeypatch.setenv("QUERY_REWRITE_ENABLED", "false")
    history = [ConversationTurn(question="What is the VPN policy?", answer="MFA is required.")]

    result = rewrite_query("Is there an exception process?", history)

    assert result.query == "Is there an exception process?"
    assert result.was_rewritten is False


def test_falls_back_to_mock_returns_original_question_unchanged() -> None:
    # conftest.py's autouse fixture pins LLM_PROVIDERS=mock, so this call falls all the
    # way to the deterministic mock provider -- no real rewrite happened.
    history = [ConversationTurn(question="What is the VPN policy?", answer="MFA is required.")]

    result = rewrite_query("Is there an exception process?", history)

    assert result.query == "Is there an exception process?"
    assert result.was_rewritten is False


def test_successful_rewrite_uses_llm_output(monkeypatch) -> None:
    captured: dict = {}

    def fake_generate(system_prompt, user_prompt, *, fallback_text, **kwargs):
        captured["user_prompt"] = user_prompt
        del system_prompt, fallback_text, kwargs

        class _Result:
            text = "What is the VPN exception process for MFA-required systems?"
            is_extractive_fallback = False

        return _Result()

    monkeypatch.setattr(query_rewriter, "llm_generate", fake_generate)
    history = [ConversationTurn(question="What is the VPN policy?", answer="MFA is required.")]

    result = rewrite_query("Is there an exception process?", history)

    assert result.query == "What is the VPN exception process for MFA-required systems?"
    assert result.was_rewritten is True
    assert "What is the VPN policy?" in captured["user_prompt"]
    assert "Is there an exception process?" in captured["user_prompt"]


def test_empty_llm_output_falls_back_to_original_question(monkeypatch) -> None:
    def fake_generate(system_prompt, user_prompt, *, fallback_text, **kwargs):
        del system_prompt, user_prompt, fallback_text, kwargs

        class _Result:
            text = "   "
            is_extractive_fallback = False

        return _Result()

    monkeypatch.setattr(query_rewriter, "llm_generate", fake_generate)
    history = [ConversationTurn(question="q1", answer="a1")]

    result = rewrite_query("follow-up", history)

    assert result.query == "follow-up"
    assert result.was_rewritten is False


def test_standalone_new_topic_question_skips_rewrite_even_with_history(monkeypatch) -> None:
    # Regression test: an earlier version relied entirely on the LLM to recognize a
    # self-contained new question and leave it alone, but in practice it would still
    # graft unrelated prior context on -- "What is the password reset policy?" asked
    # right after a Kubernetes conversation came back rewritten to ask about password
    # policy "in the Kubernetes environment," which then retrieved the wrong documents.
    # The word-count/reference-marker pre-filter must keep this from ever reaching the
    # LLM at all.
    def _fail_if_called(*args, **kwargs):
        raise AssertionError("llm_generate should not be called for a standalone question")

    monkeypatch.setattr(query_rewriter, "llm_generate", _fail_if_called)
    history = [
        ConversationTurn(
            question="What caused the Kubernetes pod crash loop?",
            answer="A ConfigMap value used text where an integer was required.",
        )
    ]

    result = rewrite_query("What is the password reset policy?", history)

    assert result.query == "What is the password reset policy?"
    assert result.was_rewritten is False


def test_short_pronoun_followup_is_detected_as_a_followup() -> None:
    from generation.query_rewriter import _looks_like_a_followup

    assert _looks_like_a_followup("How was it mitigated?") is True
    assert _looks_like_a_followup("Why did that happen?") is True
    assert _looks_like_a_followup("What about the second one?") is True


def test_standalone_question_is_not_detected_as_a_followup() -> None:
    from generation.query_rewriter import _looks_like_a_followup

    assert _looks_like_a_followup("What is the password reset policy?") is False
    assert _looks_like_a_followup("How do I troubleshoot VPN after MFA?") is False


def test_passes_fast_fail_retry_and_timeout_overrides(monkeypatch) -> None:
    captured: dict = {}

    def fake_generate(system_prompt, user_prompt, *, fallback_text, **kwargs):
        del system_prompt, user_prompt, fallback_text
        captured.update(kwargs)

        class _Result:
            text = "rewritten"
            is_extractive_fallback = False

        return _Result()

    monkeypatch.setattr(query_rewriter, "llm_generate", fake_generate)
    history = [ConversationTurn(question="q1", answer="a1")]

    rewrite_query("follow-up", history)

    assert captured["max_retries"] == 0
    assert captured["timeout_seconds"] == 6.0
