from retrieval.vector_search import retrieve_relevant_chunks


def test_retrieve_relevant_chunks_finds_vpn_sources() -> None:
    chunks = retrieve_relevant_chunks("How do I troubleshoot VPN after MFA?", top_k=3)

    assert chunks
    assert chunks[0].score > 0
    assert any("vpn" in chunk.title.lower() for chunk in chunks)


def test_retrieve_relevant_chunks_avoids_unrelated_generic_incidents() -> None:
    chunks = retrieve_relevant_chunks("What caused the VPN certificate incident?", top_k=5)

    assert chunks
    assert all("airflow" not in chunk.title.lower() for chunk in chunks)


def test_retrieve_relevant_chunks_respects_source_type_filter() -> None:
    chunks = retrieve_relevant_chunks(
        "What systems require MFA?",
        filters={"source_type": "policy"},
        top_k=5,
    )

    assert chunks
    assert all(chunk.document_id.startswith(("policy-", "governance-")) for chunk in chunks)


def test_retrieve_relevant_chunks_returns_empty_for_unknown_topic() -> None:
    chunks = retrieve_relevant_chunks("Where is the cafeteria coffee machine?", top_k=3)

    assert chunks == []
