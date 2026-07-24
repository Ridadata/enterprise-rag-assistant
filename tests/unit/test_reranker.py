import sys
import types

from retrieval import reranker
from retrieval.reranker import rerank_chunks
from retrieval.vector_search import RetrievedChunk


def _chunk(chunk_id: str, content: str, score: float = 0.5) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id=chunk_id.split("::")[0],
        title="Title",
        content=content,
        score=score,
        source_type="ticket",
    )


def _install_fake_cross_encoder(monkeypatch, predict):
    class _FakeCrossEncoder:
        def __init__(self, model_name):
            del model_name

        def predict(self, pairs):
            return predict(pairs)

    fake_module = types.ModuleType("sentence_transformers")
    fake_module.CrossEncoder = _FakeCrossEncoder
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)
    reranker._load_cross_encoder.cache_clear()


def test_empty_chunks_returns_empty() -> None:
    result = rerank_chunks("question", [], top_k=5, model_name="fake-model")

    assert result == []


def test_missing_sdk_falls_back_to_first_top_k_unchanged(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)
    reranker._load_cross_encoder.cache_clear()
    chunks = [_chunk("doc-1::0", "a"), _chunk("doc-2::0", "b"), _chunk("doc-3::0", "c")]

    result = rerank_chunks("question", chunks, top_k=2, model_name="fake-model")

    assert result == chunks[:2]


def test_reorders_by_cross_encoder_score(monkeypatch) -> None:
    # The first-stage order (by chunk.score) disagrees with what the "cross-encoder"
    # says is actually relevant -- reranking should flip the order to match it.
    chunks = [
        _chunk("doc-1::0", "irrelevant filler", score=0.9),
        _chunk("doc-2::0", "the actually relevant content", score=0.3),
    ]

    def predict(pairs):
        return [-5.0 if "irrelevant" in content else 5.0 for _question, content in pairs]

    _install_fake_cross_encoder(monkeypatch, predict)

    result = rerank_chunks("question", chunks, top_k=2, model_name="fake-model")

    assert [chunk.chunk_id for chunk in result] == ["doc-2::0", "doc-1::0"]
    # Scores are sigmoid-normalized into [0, 1], not left as raw logits.
    assert 0.0 <= result[0].score <= 1.0
    assert result[0].score > result[1].score


def test_min_score_filters_out_low_scoring_candidates(monkeypatch) -> None:
    chunks = [_chunk("doc-1::0", "relevant", score=0.5), _chunk("doc-2::0", "unrelated", score=0.5)]

    def predict(pairs):
        return [5.0 if "relevant" in content else -5.0 for _question, content in pairs]

    _install_fake_cross_encoder(monkeypatch, predict)

    result = rerank_chunks("question", chunks, top_k=5, model_name="fake-model", min_score=0.5)

    assert len(result) == 1
    assert result[0].chunk_id == "doc-1::0"


def test_truncates_to_top_k_after_rerank(monkeypatch) -> None:
    chunks = [_chunk(f"doc-{i}::0", f"content {i}", score=0.5) for i in range(5)]

    _install_fake_cross_encoder(monkeypatch, lambda pairs: [float(i) for i in range(len(pairs))])

    result = rerank_chunks("question", chunks, top_k=2, model_name="fake-model")

    assert len(result) == 2


def test_inference_failure_falls_back_to_first_top_k_unchanged(monkeypatch) -> None:
    class _RaisingCrossEncoder:
        def __init__(self, model_name):
            del model_name

        def predict(self, pairs):
            raise RuntimeError("inference failed")

    fake_module = types.ModuleType("sentence_transformers")
    fake_module.CrossEncoder = _RaisingCrossEncoder
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)
    reranker._load_cross_encoder.cache_clear()

    chunks = [_chunk("doc-1::0", "a"), _chunk("doc-2::0", "b")]

    result = rerank_chunks("question", chunks, top_k=5, model_name="fake-model")

    assert result == chunks[:5]
