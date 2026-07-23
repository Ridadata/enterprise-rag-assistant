def vector_to_pgvector(vector: list[float]) -> str:
    """Format a Python vector as a pgvector literal, e.g. '[0.100000,-0.200000]'."""
    return "[" + ",".join(f"{value:.6f}" for value in vector) + "]"
