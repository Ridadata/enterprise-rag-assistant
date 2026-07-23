def expected_source_hit(retrieved_document_ids: list[str], expected_document_ids: list[str]) -> bool:
    """Whether at least one retrieved chunk came from an expected document."""
    if not expected_document_ids:
        return False
    return any(document_id in expected_document_ids for document_id in retrieved_document_ids)


def precision_at_k(retrieved_document_ids: list[str], expected_document_ids: list[str]) -> float:
    """Fraction of retrieved chunks that came from an expected document."""
    if not retrieved_document_ids:
        return 0.0
    hits = sum(1 for document_id in retrieved_document_ids if document_id in expected_document_ids)
    return hits / len(retrieved_document_ids)


def recall_at_k(retrieved_document_ids: list[str], expected_document_ids: list[str]) -> float:
    """Fraction of expected documents that appear anywhere among the retrieved chunks."""
    if not expected_document_ids:
        return 0.0
    hits = sum(1 for document_id in expected_document_ids if document_id in retrieved_document_ids)
    return hits / len(expected_document_ids)


def is_idk_response(answer_text: str) -> bool:
    return answer_text.strip().lower().startswith("i do not know")


def mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def percentile(values: list[float], fraction: float) -> float:
    """Nearest-rank percentile, e.g. percentile(values, 0.95) for p95."""
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round(fraction * (len(ordered) - 1)))
    return round(ordered[index], 2)
