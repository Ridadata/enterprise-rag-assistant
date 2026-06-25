from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    title: str
    content: str
    score: float


def retrieve_relevant_chunks(
    question: str,
    filters: dict[str, str | list[str]] | None = None,
    top_k: int = 5,
) -> list[RetrievedChunk]:
    """Temporary retrieval stub until pgvector-backed search is implemented."""
    _ = filters
    normalized = question.lower()
    if "vpn" not in normalized and "password" not in normalized and "backup" not in normalized:
        return []

    sample = RetrievedChunk(
        chunk_id="chunk-demo-001",
        document_id="runbook-vpn-001",
        title="VPN Connectivity Runbook",
        content=(
            "For VPN connection failures, verify MFA status, check the client version, "
            "confirm DNS resolution, restart the VPN client, and escalate to Network "
            "Operations if authentication succeeds but tunnel creation fails."
        ),
        score=0.72,
    )
    return [sample][:top_k]

