import logging
import math
from dataclasses import replace
from functools import lru_cache

from retrieval.vector_search import RetrievedChunk

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_cross_encoder(model_name: str):
    # Imported lazily so importing this module never requires sentence-transformers/torch
    # unless reranking is actually enabled -- same pattern as the embedding provider.
    from sentence_transformers import CrossEncoder

    return CrossEncoder(model_name)


def _sigmoid(x: float) -> float:
    # Cross-encoder models are trained with a raw logit output, not a probability -- this
    # maps that logit into [0,1] so it's comparable to (and can reuse the same UI/threshold
    # conventions as) the first-stage hybrid/keyword score.
    return 1.0 / (1.0 + math.exp(-x))


def rerank_chunks(
    question: str,
    chunks: list[RetrievedChunk],
    *,
    top_k: int,
    model_name: str,
    min_score: float = 0.0,
) -> list[RetrievedChunk]:
    """Re-scores each candidate directly against the question with a cross-encoder,
    replacing the first-stage score, then re-sorts and trims to top_k.

    This is deliberately a second pass over an already-filtered candidate list, not a
    replacement for first-stage retrieval: a cross-encoder scores every (question, chunk)
    pair individually (no precomputed vectors), so it doesn't scale to searching a whole
    corpus, but it's far more precise than first-stage vector/keyword overlap at telling
    "this chunk actually answers the question" apart from "this chunk shares some words
    with it" -- which is exactly what keeps a follow-up question from dragging in
    documents that merely look related.

    Falls back to the first `top_k` candidates unchanged (in their original order) if the
    model isn't installed or fails to load, rather than raising -- a missing reranker
    should degrade retrieval quality, not break the request.
    """
    if not chunks:
        return chunks

    try:
        encoder = _load_cross_encoder(model_name)
    except ImportError:
        logger.warning("sentence-transformers not installed; skipping rerank.")
        return chunks[:top_k]
    except Exception:
        logger.exception("Failed to load cross-encoder %r; skipping rerank.", model_name)
        return chunks[:top_k]

    try:
        pairs = [(question, chunk.content) for chunk in chunks]
        raw_scores = encoder.predict(pairs)
    except Exception:
        logger.exception("Cross-encoder inference failed; skipping rerank.")
        return chunks[:top_k]

    rescored = [
        replace(chunk, score=round(_sigmoid(float(raw)), 4)) for chunk, raw in zip(chunks, raw_scores)
    ]
    rescored.sort(key=lambda chunk: chunk.score, reverse=True)
    filtered = [chunk for chunk in rescored if chunk.score >= min_score]
    return filtered[:top_k]
