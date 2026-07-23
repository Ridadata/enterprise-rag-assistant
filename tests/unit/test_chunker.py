import pytest

from ingestion.chunking.simple_chunker import CHUNK_CONFIG_BY_SOURCE_TYPE, chunk_text


def test_chunk_text_splits_content_by_word_limit() -> None:
    content = " ".join(str(index) for index in range(12))

    chunks = chunk_text(content, max_words=5)

    assert len(chunks) == 3
    assert chunks[2].content == "10 11"


def test_chunk_text_overlaps_consecutive_chunks_when_overlap_words_given() -> None:
    content = " ".join(str(index) for index in range(25))

    chunks = chunk_text(content, max_words=10, overlap_words=3)

    assert len(chunks) == 4
    assert chunks[0].content.split()[-3:] == ["7", "8", "9"]
    assert chunks[1].content.split()[:3] == ["7", "8", "9"]


def test_chunk_text_rejects_overlap_not_smaller_than_max_words() -> None:
    with pytest.raises(ValueError, match="overlap_words"):
        chunk_text("some content here", max_words=5, overlap_words=5)


def test_chunk_text_returns_empty_list_for_blank_content() -> None:
    assert chunk_text("") == []
    assert chunk_text("   \n\t  ") == []


def test_chunk_text_uses_source_type_config_when_no_explicit_override() -> None:
    content = " ".join(str(index) for index in range(500))

    ticket_chunks = chunk_text(content, source_type="ticket")
    runbook_chunks = chunk_text(content, source_type="runbook")
    unknown_type_chunks = chunk_text(content, source_type="not-a-real-type")

    ticket_config = CHUNK_CONFIG_BY_SOURCE_TYPE["ticket"]
    assert len(ticket_chunks[0].content.split()) == ticket_config.max_words
    assert len(runbook_chunks) == 1  # 500 words fits in one runbook-sized chunk (650 words)
    assert len(unknown_type_chunks) == len(chunk_text(content))  # falls back to the default config


def test_chunk_text_explicit_max_words_overrides_source_type_config() -> None:
    content = " ".join(str(index) for index in range(20))

    chunks = chunk_text(content, source_type="runbook", max_words=5, overlap_words=0)

    assert len(chunks) == 4


def test_chunk_text_token_count_approximates_real_tokens_not_word_count() -> None:
    content = "a" * 40  # single 40-character "word", ~10 tokens at 4 chars/token

    chunks = chunk_text(content, max_words=100)

    assert len(chunks) == 1
    assert chunks[0].token_count == 10
