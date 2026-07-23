from functools import lru_cache

from database.settings import get_settings
from ingestion.embedding.format import vector_to_pgvector


EMBEDDING_DIMENSION = 384

__all__ = ["EMBEDDING_DIMENSION", "embed_text", "vector_to_pgvector"]


@lru_cache(maxsize=1)
def _load_model():
    # Imported lazily so importing this module never requires torch/sentence-transformers
    # unless the sentence_transformers embedding provider is actually selected.
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(get_settings().embedding_model)


def embed_text(text: str) -> list[float]:
    """Real semantic embedding via a sentence-transformers model (downloaded/cached on first use)."""
    model = _load_model()
    vector = model.encode(text, normalize_embeddings=True)
    return vector.tolist()
