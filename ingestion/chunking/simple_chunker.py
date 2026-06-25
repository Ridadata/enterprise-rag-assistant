from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    chunk_index: int
    section_title: str
    content: str
    token_count: int


def chunk_text(content: str, section_title: str = "body", max_words: int = 350) -> list[TextChunk]:
    words = content.split()
    chunks: list[TextChunk] = []
    for index, start in enumerate(range(0, len(words), max_words)):
        chunk_words = words[start : start + max_words]
        chunks.append(
            TextChunk(
                chunk_index=index,
                section_title=section_title,
                content=" ".join(chunk_words),
                token_count=len(chunk_words),
            )
        )
    return chunks

