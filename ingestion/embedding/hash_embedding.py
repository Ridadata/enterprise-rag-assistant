import hashlib
import math
import re

from ingestion.embedding.format import vector_to_pgvector


EMBEDDING_DIMENSION = 384
EMBEDDING_MODEL_NAME = "hashing-384-v1"

__all__ = ["EMBEDDING_DIMENSION", "EMBEDDING_MODEL_NAME", "embed_text", "vector_to_pgvector"]


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def embed_text(text: str, dimension: int = EMBEDDING_DIMENSION) -> list[float]:
    """Create a deterministic local embedding without downloading a model."""
    vector = [0.0] * dimension

    for token in _tokens(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimension
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [round(value / norm, 6) for value in vector]

