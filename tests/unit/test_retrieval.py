from retrieval.vector_search import retrieve_local_chunks

# These tests exercise the local keyword-search backend's specific heuristics (title/tag
# bonus, stop-word handling, source-type diversification) directly via
# retrieve_local_chunks, rather than through the auto-dispatching retrieve_relevant_chunks.
# That keeps them hermetic: they'd otherwise silently pick up whatever real Postgres
# instance happens to be reachable on the machine running them.


def test_retrieve_local_chunks_finds_vpn_sources() -> None:
    chunks = retrieve_local_chunks("How do I troubleshoot VPN after MFA?", top_k=3)

    assert chunks
    assert chunks[0].score > 0
    assert any("vpn" in chunk.title.lower() for chunk in chunks)


def test_retrieve_local_chunks_avoids_unrelated_generic_incidents() -> None:
    chunks = retrieve_local_chunks("What caused the VPN certificate incident?", top_k=5)

    assert chunks
    assert all("airflow" not in chunk.title.lower() for chunk in chunks)


def test_retrieve_local_chunks_diversifies_source_types() -> None:
    chunks = retrieve_local_chunks("How do I fix Docker build 401 from private package registry?", top_k=5)

    assert len(chunks) >= 3
    assert len({chunk.source_type for chunk in chunks}) >= 3


def test_retrieve_local_chunks_respects_source_type_filter() -> None:
    chunks = retrieve_local_chunks(
        "What systems require MFA?",
        filters={"source_type": "policy"},
        top_k=5,
    )

    assert chunks
    assert all(chunk.document_id.startswith(("policy-", "governance-")) for chunk in chunks)


def test_retrieve_local_chunks_returns_empty_for_unknown_topic() -> None:
    chunks = retrieve_local_chunks("Where is the cafeteria coffee machine?", top_k=3)

    assert chunks == []
