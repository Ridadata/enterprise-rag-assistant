from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    chunk_index: int
    section_title: str
    content: str
    token_count: int


@dataclass(frozen=True)
class ChunkConfig:
    max_words: int
    overlap_words: int


DEFAULT_CHUNK_CONFIG = ChunkConfig(max_words=350, overlap_words=0)

# Word-based approximation of project_plan.md's per-document-type chunk size/overlap table
# (tickets/runbooks/policies/vendor docs/CVE records each get different size and overlap).
CHUNK_CONFIG_BY_SOURCE_TYPE: dict[str, ChunkConfig] = {
    "ticket": ChunkConfig(max_words=400, overlap_words=50),
    "incident_report": ChunkConfig(max_words=400, overlap_words=50),
    "runbook": ChunkConfig(max_words=650, overlap_words=100),
    "policy": ChunkConfig(max_words=750, overlap_words=100),
    "adr": ChunkConfig(max_words=750, overlap_words=100),
    "wiki": ChunkConfig(max_words=750, overlap_words=100),
    "faq": ChunkConfig(max_words=750, overlap_words=100),
    "vendor_doc": ChunkConfig(max_words=850, overlap_words=120),
    "cve": ChunkConfig(max_words=300, overlap_words=25),
}


def _chunk_config_for(source_type: str | None) -> ChunkConfig:
    if source_type is None:
        return DEFAULT_CHUNK_CONFIG
    return CHUNK_CONFIG_BY_SOURCE_TYPE.get(source_type.lower(), DEFAULT_CHUNK_CONFIG)


def _estimate_token_count(text: str) -> int:
    """Approximate LLM token count using the standard ~4-characters-per-token heuristic.

    Avoids pulling in a real tokenizer dependency; good enough for cost/context-budget
    estimates, unlike the previous plain word count which understated usage.
    """
    if not text:
        return 0
    return max(1, round(len(text) / 4))


def chunk_text(
    content: str,
    section_title: str = "body",
    source_type: str | None = None,
    max_words: int | None = None,
    overlap_words: int | None = None,
) -> list[TextChunk]:
    config = _chunk_config_for(source_type)
    words_per_chunk = max_words if max_words is not None else config.max_words
    overlap = overlap_words if overlap_words is not None else config.overlap_words
    if words_per_chunk <= 0:
        raise ValueError("max_words must be positive")
    if overlap < 0 or overlap >= words_per_chunk:
        raise ValueError("overlap_words must be in [0, max_words)")

    words = content.split()
    if not words:
        return []

    step = words_per_chunk - overlap
    chunks: list[TextChunk] = []
    start = 0
    index = 0
    while True:
        chunk_words = words[start : start + words_per_chunk]
        text = " ".join(chunk_words)
        chunks.append(
            TextChunk(
                chunk_index=index,
                section_title=section_title,
                content=text,
                token_count=_estimate_token_count(text),
            )
        )
        if start + words_per_chunk >= len(words):
            break
        index += 1
        start += step

    return chunks
