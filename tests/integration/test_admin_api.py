from datetime import datetime

from fastapi.testclient import TestClient

from api.main import app
from api.schemas.admin import AdminSummary, IngestionStatusCount
from tests.conftest import TEST_API_KEY


client = TestClient(app)
AUTH_HEADERS = {"X-API-Key": TEST_API_KEY}


def test_admin_summary_returns_expected_shape(monkeypatch) -> None:
    import api.routes.admin as admin_route

    monkeypatch.setattr(
        admin_route,
        "get_admin_summary",
        lambda: AdminSummary(
            retrieval_backend="auto",
            total_queries=42,
            mean_latency_ms=123.4,
            p95_latency_ms=250.0,
            confidence_counts={"high": 20, "medium": 15, "low": 7},
            idk_rate=0.1,
            total_tokens_in=1000,
            total_tokens_out=500,
            total_cost_estimate=0.05,
            queries_by_day=[],
            most_cited_documents=[],
            never_retrieved_document_count=3,
            ingestion_status_counts=[IngestionStatusCount(status="ingested", count=115)],
            most_recent_ingestion_at=datetime(2026, 7, 22, 13, 9, 27),
        ),
    )

    response = client.get("/admin/summary", headers=AUTH_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_queries"] == 42
    assert payload["confidence_counts"] == {"high": 20, "medium": 15, "low": 7}
    assert payload["ingestion_status_counts"] == [{"status": "ingested", "count": 115}]
    assert payload["retrieval_backend"] == "auto"


def test_admin_summary_returns_503_when_postgres_unreachable(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://rag_user:rag_password@localhost:1/enterprise_rag")

    response = client.get("/admin/summary", headers=AUTH_HEADERS)

    assert response.status_code == 503


def test_admin_summary_rejects_requests_without_api_key() -> None:
    response = client.get("/admin/summary")

    assert response.status_code == 401
