from fastapi.testclient import TestClient

from api.main import app
from api.schemas.corpus import CorpusSummary
from tests.conftest import TEST_API_KEY


client = TestClient(app)
AUTH_HEADERS = {"X-API-Key": TEST_API_KEY}


def test_corpus_summary_returns_expected_shape(monkeypatch) -> None:
    import api.routes.corpus as corpus_route

    monkeypatch.setattr(
        corpus_route,
        "get_corpus_summary",
        lambda: CorpusSummary(document_count=115, chunk_count=115, source_types={"ticket": 60}),
    )

    response = client.get("/corpus/summary", headers=AUTH_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload == {"document_count": 115, "chunk_count": 115, "source_types": {"ticket": 60}}


def test_corpus_summary_returns_503_when_postgres_unreachable(monkeypatch) -> None:
    # Port 1 is deterministically unreachable regardless of what's actually running on
    # the machine (unlike relying on "no DB happens to be up" as ambient state).
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://rag_user:rag_password@localhost:1/enterprise_rag")

    response = client.get("/corpus/summary", headers=AUTH_HEADERS)

    assert response.status_code == 503


def test_corpus_summary_rejects_requests_without_api_key() -> None:
    response = client.get("/corpus/summary")

    assert response.status_code == 401
