from collections.abc import Callable
from dataclasses import dataclass

from database.settings import get_settings
from ingestion.embedding import hash_embedding, sentence_transformer_embedding


@dataclass(frozen=True)
class EmbeddingProvider:
    """A concrete embedding backend: the model identity plus its embed/format functions."""

    model_name: str
    dimension: int
    embed_text: Callable[[str], list[float]]
    vector_to_pgvector: Callable[[list[float]], str]


def _hash_provider() -> EmbeddingProvider:
    return EmbeddingProvider(
        model_name=hash_embedding.EMBEDDING_MODEL_NAME,
        dimension=hash_embedding.EMBEDDING_DIMENSION,
        embed_text=hash_embedding.embed_text,
        vector_to_pgvector=hash_embedding.vector_to_pgvector,
    )


def _sentence_transformers_provider() -> EmbeddingProvider:
    return EmbeddingProvider(
        model_name=get_settings().embedding_model,
        dimension=sentence_transformer_embedding.EMBEDDING_DIMENSION,
        embed_text=sentence_transformer_embedding.embed_text,
        vector_to_pgvector=sentence_transformer_embedding.vector_to_pgvector,
    )


_PROVIDER_FACTORIES: dict[str, Callable[[], EmbeddingProvider]] = {
    "hash": _hash_provider,
    "sentence_transformers": _sentence_transformers_provider,
}


def get_embedding_provider(provider: str | None = None) -> EmbeddingProvider:
    """Resolve the configured embedding backend.

    `provider` overrides `EMBEDDING_PROVIDER`/settings -- pass "hash" explicitly in tests
    to avoid loading a real sentence-transformers model.
    """
    key = (provider or get_settings().embedding_provider).lower()
    try:
        factory = _PROVIDER_FACTORIES[key]
    except KeyError:
        raise ValueError(
            f"Unknown EMBEDDING_PROVIDER {key!r}; expected one of {sorted(_PROVIDER_FACTORIES)}"
        ) from None
    return factory()
