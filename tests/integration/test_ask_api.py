from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_ask_returns_grounded_answer_with_sources() -> None:
    response = client.post("/ask", json={"question": "How do I troubleshoot VPN after MFA?"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"].startswith("Based on the retrieved sources:")
    assert payload["confidence"] in {"medium", "high"}
    assert payload["sources"]
    assert any("vpn" in source["title"].lower() for source in payload["sources"])


def test_ask_returns_i_do_not_know_when_context_is_missing() -> None:
    response = client.post("/ask", json={"question": "Where is the cafeteria coffee machine?"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "I do not know based on the available documents."
    assert payload["confidence"] == "low"
    assert payload["sources"] == []

