import pytest

from ingestion.embedding.provider import get_embedding_provider


def test_hash_provider_is_deterministic_and_384_dimensions() -> None:
    provider = get_embedding_provider("hash")

    assert provider.model_name == "hashing-384-v1"
    assert provider.dimension == 384
    assert provider.embed_text("VPN MFA") == provider.embed_text("VPN MFA")


def test_sentence_transformers_provider_reports_model_identity_without_loading_the_model() -> None:
    # Only .model_name/.dimension are touched here -- embed_text() is what lazily loads
    # the real model, so this stays fast and network-free.
    provider = get_embedding_provider("sentence_transformers")

    assert provider.model_name == "sentence-transformers/all-MiniLM-L6-v2"
    assert provider.dimension == 384


def test_unknown_provider_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unknown EMBEDDING_PROVIDER"):
        get_embedding_provider("not-a-real-provider")
