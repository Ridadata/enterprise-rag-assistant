from ingestion.embedding.hash_embedding import EMBEDDING_DIMENSION, embed_text, vector_to_pgvector


def test_hash_embedding_is_deterministic_and_384_dimensions() -> None:
    first = embed_text("VPN MFA certificate rotation")
    second = embed_text("VPN MFA certificate rotation")

    assert first == second
    assert len(first) == EMBEDDING_DIMENSION
    assert any(value != 0 for value in first)


def test_vector_to_pgvector_formats_vector_literal() -> None:
    vector = [0.1, -0.2, 0.0]

    assert vector_to_pgvector(vector) == "[0.100000,-0.200000,0.000000]"

