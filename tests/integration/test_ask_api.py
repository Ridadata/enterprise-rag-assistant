from fastapi.testclient import TestClient

from api.main import app
from tests.conftest import TEST_API_KEY


client = TestClient(app)
AUTH_HEADERS = {"X-API-Key": TEST_API_KEY}


def test_ask_returns_grounded_answer_with_sources() -> None:
    response = client.post(
        "/ask", json={"question": "How do I troubleshoot VPN after MFA?"}, headers=AUTH_HEADERS
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"].startswith("Based on the retrieved sources:")
    assert payload["confidence"] in {"medium", "high"}
    assert payload["sources"]
    assert any("vpn" in source["title"].lower() for source in payload["sources"])
    assert all(source["chunk_position"] >= 1 for source in payload["sources"])
    assert payload["latency_ms"] >= 0
    assert payload["model_name"] == "mock-grounded-answer"
    # No history was sent, so the retrieval query is the question verbatim; the mock
    # provider never produces real follow-up suggestions (see answer_generator.py).
    assert payload["retrieval_query"] == "How do I troubleshoot VPN after MFA?"
    assert payload["follow_up_questions"] == []


def test_ask_accepts_conversation_history_for_follow_up_questions() -> None:
    response = client.post(
        "/ask",
        json={
            "question": "Is there an exception process?",
            "history": [
                {
                    "question": "What is the VPN policy?",
                    "answer": "All remote access requires MFA.",
                }
            ],
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    payload = response.json()
    # conftest.py pins LLM_PROVIDERS=mock, so rewriting always falls back to the raw
    # question -- this asserts the history field round-trips through the API without
    # erroring, not that a real rewrite happened (see tests/unit/test_query_rewriter.py
    # for that, with a fake real provider).
    assert payload["retrieval_query"] == "Is there an exception process?"


def test_ask_returns_i_do_not_know_when_context_is_missing(monkeypatch) -> None:
    # Pinned to the local keyword backend: this is testing the API's IDK contract, not
    # embedding quality, so it shouldn't depend on whatever real Postgres/embedding model
    # is (or isn't) reachable on the machine running the test.
    monkeypatch.setenv("RAG_RETRIEVAL_BACKEND", "local")

    response = client.post(
        "/ask", json={"question": "Where is the cafeteria coffee machine?"}, headers=AUTH_HEADERS
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "I do not know based on the available documents."
    assert payload["confidence"] == "low"
    assert payload["sources"] == []
    assert payload["model_name"] == "n/a"


def test_ask_rejects_unknown_filter_keys() -> None:
    response = client.post(
        "/ask",
        json={"question": "How do I reset my password?", "filters": {"not_a_real_filter": "x"}},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422


def test_ask_returns_503_when_postgres_backend_is_pinned_and_unreachable(monkeypatch) -> None:
    monkeypatch.setenv("RAG_RETRIEVAL_BACKEND", "postgres")
    # Port 1 is a reserved/privileged port nothing will ever be listening on, so this is
    # deterministically unreachable regardless of what's actually running on the machine
    # (unlike relying on "no DB happens to be up" as ambient state).
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://rag_user:rag_password@localhost:1/enterprise_rag")

    response = client.post(
        "/ask", json={"question": "How do I troubleshoot VPN after MFA?"}, headers=AUTH_HEADERS
    )

    assert response.status_code == 503


def test_ask_rejects_requests_without_api_key() -> None:
    response = client.post("/ask", json={"question": "How do I troubleshoot VPN after MFA?"})

    assert response.status_code == 401


def test_ask_rejects_requests_with_wrong_api_key() -> None:
    response = client.post(
        "/ask",
        json={"question": "How do I troubleshoot VPN after MFA?"},
        headers={"X-API-Key": "wrong-key"},
    )

    assert response.status_code == 401
