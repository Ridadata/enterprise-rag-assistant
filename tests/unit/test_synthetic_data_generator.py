from scripts.generate_synthetic_data import generate_documents


def test_generate_documents_creates_project_ready_corpus() -> None:
    documents = generate_documents()

    assert len(documents) >= 100
    assert {document["source_type"] for document in documents} >= {
        "ticket",
        "runbook",
        "policy",
        "incident_report",
        "wiki",
        "adr",
        "faq",
    }
    assert all(document["content"] for document in documents)

