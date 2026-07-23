from datetime import date, datetime

from monitoring import analytics


class _FakeCursor:
    def __init__(self, results: list) -> None:
        self._results = list(results)
        self._last = None

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def execute(self, sql: str, params: tuple = ()) -> None:
        self._last = self._results.pop(0)

    def fetchone(self):
        return self._last

    def fetchall(self):
        return self._last


class _FakeConnection:
    def __init__(self, results: list) -> None:
        self._results = results

    def __enter__(self) -> "_FakeConnection":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self._results)


class _FakePsycopg:
    def __init__(self, connection: _FakeConnection) -> None:
        self._connection = connection

    def connect(self, database_url: str, connect_timeout: int | None = None) -> _FakeConnection:
        return self._connection


def test_get_admin_summary_maps_all_queries_correctly(monkeypatch) -> None:
    results = [
        (42,),  # total_queries
        (123.45, 250.0),  # mean/p95 latency
        [("high", 20), ("medium", 15), ("low", 7)],  # confidence counts
        [
            ("Based on the retrieved sources: do X.",),
            ("I do not know based on the available documents.",),
            ("Based on the retrieved sources: do Y.",),
        ],  # answer texts, for IDK-rate detection
        (1000, 500, 0.05),  # token/cost sums
        [(date(2026, 7, 20), 10), (date(2026, 7, 21), 32)],  # queries by day
        [("doc-1", "VPN Runbook", 5), ("doc-2", "MFA Policy", 3)],  # most cited
        (12,),  # never-retrieved document count
        [("ingested", 110), ("pending", 5)],  # ingestion status counts
        (datetime(2026, 7, 22, 13, 9, 27),),  # most recent ingestion timestamp
    ]
    connection = _FakeConnection(results)
    fake_psycopg = _FakePsycopg(connection)
    monkeypatch.setattr(analytics, "_import_psycopg", lambda: fake_psycopg)

    summary = analytics.get_admin_summary(database_url="postgresql://fake")

    assert summary.total_queries == 42
    assert summary.mean_latency_ms == 123.45
    assert summary.p95_latency_ms == 250.0
    assert summary.confidence_counts == {"high": 20, "medium": 15, "low": 7}
    assert summary.idk_rate == round(1 / 3, 4)
    assert summary.total_tokens_in == 1000
    assert summary.total_tokens_out == 500
    assert summary.total_cost_estimate == 0.05
    assert summary.queries_by_day == [
        analytics.QueryVolumePoint(day=date(2026, 7, 20), query_count=10),
        analytics.QueryVolumePoint(day=date(2026, 7, 21), query_count=32),
    ]
    assert summary.most_cited_documents == [
        analytics.CitedDocument(document_id="doc-1", title="VPN Runbook", citation_count=5),
        analytics.CitedDocument(document_id="doc-2", title="MFA Policy", citation_count=3),
    ]
    assert summary.never_retrieved_document_count == 12
    assert summary.ingestion_status_counts == [
        analytics.IngestionStatusCount(status="ingested", count=110),
        analytics.IngestionStatusCount(status="pending", count=5),
    ]
    assert summary.most_recent_ingestion_at == datetime(2026, 7, 22, 13, 9, 27)


def test_get_admin_summary_handles_empty_database(monkeypatch) -> None:
    results = [
        (0,),
        (None, None),
        [],
        [],
        (0, 0, 0),
        [],
        [],
        (0,),
        [],
        (None,),
    ]
    connection = _FakeConnection(results)
    fake_psycopg = _FakePsycopg(connection)
    monkeypatch.setattr(analytics, "_import_psycopg", lambda: fake_psycopg)

    summary = analytics.get_admin_summary(database_url="postgresql://fake")

    assert summary.total_queries == 0
    assert summary.mean_latency_ms is None
    assert summary.p95_latency_ms is None
    assert summary.confidence_counts == {}
    assert summary.idk_rate == 0.0
    assert summary.most_cited_documents == []
    assert summary.never_retrieved_document_count == 0
    assert summary.ingestion_status_counts == []
    assert summary.most_recent_ingestion_at is None
