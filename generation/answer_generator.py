from api.schemas.qa import AskResponse
from generation.citation_builder import citations_from_chunks
from retrieval.vector_search import RetrievedChunk


def build_grounded_answer(question: str, chunks: list[RetrievedChunk]) -> AskResponse:
    _ = question
    if not chunks:
        return AskResponse(
            answer="I do not know based on the available documents.",
            confidence="low",
            limitations="No retrieved source passed the minimum evidence threshold.",
            next_step="Add relevant documents or broaden the search filters, then ask again.",
            sources=[],
        )

    return AskResponse(
        answer=(
            "Based on the retrieved runbook, start by checking MFA status, VPN client "
            "version, DNS resolution, and whether the VPN tunnel is created after "
            "authentication. Escalate to Network Operations if authentication succeeds "
            "but tunnel creation still fails."
        ),
        confidence="medium",
        limitations="This starter response uses the retrieval stub until the LLM layer is wired.",
        next_step="Implement pgvector retrieval and replace the mock generator with a grounded LLM call.",
        sources=citations_from_chunks(chunks),
    )

