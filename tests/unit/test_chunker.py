from ingestion.chunking.simple_chunker import chunk_text


def test_chunk_text_splits_content_by_word_limit() -> None:
    content = " ".join(str(index) for index in range(12))

    chunks = chunk_text(content, max_words=5)

    assert len(chunks) == 3
    assert chunks[0].token_count == 5
    assert chunks[2].content == "10 11"

