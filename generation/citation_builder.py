from api.schemas.qa import SourceCitation
from retrieval.vector_search import RetrievedChunk


def citations_from_chunks(chunks: list[RetrievedChunk]) -> list[SourceCitation]:
    citations: list[SourceCitation] = []
    for chunk in chunks:
        citations.append(
            SourceCitation(
                document_id=chunk.document_id,
                title=chunk.title,
                chunk_id=chunk.chunk_id,
                excerpt=chunk.content[:240],
                score=chunk.score,
            )
        )
    return citations

