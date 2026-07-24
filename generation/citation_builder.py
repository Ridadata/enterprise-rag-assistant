from api.schemas.qa import SourceCitation
from retrieval.vector_search import RetrievedChunk


def citations_from_chunks(chunks: list[RetrievedChunk]) -> list[SourceCitation]:
    citations: list[SourceCitation] = []
    for chunk in chunks:
        citations.append(
            SourceCitation(
                document_id=chunk.document_id,
                title=chunk.title,
                # Full chunk content, not a truncated preview -- the UI line-clamps it in
                # the compact citation card and shows it in full when a citation is
                # expanded (see web/components/search/citation-card.tsx), so there's no
                # server-side reason to cut it short here.
                excerpt=chunk.content,
                chunk_id=chunk.chunk_id,
                score=chunk.score,
                chunk_position=chunk.chunk_index + 1,
            )
        )
    return citations

