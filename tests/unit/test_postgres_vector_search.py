import logging

import pytest

from retrieval import postgres_vector_search as pvs


class _FakeCursor:
    def __init__(self, rows: list[tuple]) -> None:
        self.rows = rows
        self.last_sql: str | None = None
        self.last_params: list | None = None

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def execute(self, sql: str, params: list) -> None:
        self.last_sql = sql
        self.last_params = params

    def fetchall(self) -> list[tuple]:
        return self.rows


class _FakeConnection:
    def __init__(self, rows: list[tuple]) -> None:
        self._cursor = _FakeCursor(rows)

    def __enter__(self) -> "_FakeConnection":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def cursor(self) -> _FakeCursor:
        return self._cursor


class _FakePsycopg:
    def __init__(self, rows: list[tuple] | None = None, connect_error: Exception | None = None) -> None:
        self.rows = rows or []
        self.connect_error = connect_error
        self.connections: list[_FakeConnection] = []

    def connect(self, database_url: str, connect_timeout: int | None = None) -> _FakeConnection:
        if self.connect_error:
            raise self.connect_error
        connection = _FakeConnection(self.rows)
        self.connections.append(connection)
        return connection


def test_retrieve_postgres_chunks_maps_rows_to_retrieved_chunks(monkeypatch) -> None:
    fake_rows = [
        ("doc-1::0", "doc-1", "VPN Runbook", "runbook", "VPN troubleshooting content", 0.8123),
    ]
    fake_psycopg = _FakePsycopg(rows=fake_rows)
    monkeypatch.setattr(pvs, "_import_psycopg", lambda: fake_psycopg)

    chunks = pvs.retrieve_postgres_chunks(
        "How do I fix VPN?",
        top_k=5,
        min_score=0.3,
        database_url="postgresql://fake",
        embedding_provider="hash",
    )

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.chunk_id == "doc-1::0"
    assert chunk.document_id == "doc-1"
    assert chunk.title == "VPN Runbook"
    assert chunk.source_type == "runbook"
    assert chunk.content == "VPN troubleshooting content"
    assert chunk.score == 0.8123


def test_retrieve_postgres_chunks_filters_before_limit_in_sql(monkeypatch) -> None:
    fake_psycopg = _FakePsycopg(rows=[])
    monkeypatch.setattr(pvs, "_import_psycopg", lambda: fake_psycopg)

    pvs.retrieve_postgres_chunks(
        "question",
        top_k=7,
        min_score=0.42,
        database_url="postgresql://fake",
        embedding_provider="hash",
    )

    cursor = fake_psycopg.connections[0].cursor()
    assert "WHERE hybrid_score >= %s" in cursor.last_sql
    assert cursor.last_sql.index("WHERE hybrid_score >= %s") < cursor.last_sql.index("LIMIT %s")
    # min_score and top_k are the last two bound params, in that order.
    assert cursor.last_params[-2:] == [0.42, 7]


def test_retrieve_postgres_chunks_builds_category_and_tags_filter_sql(monkeypatch) -> None:
    fake_psycopg = _FakePsycopg(rows=[])
    monkeypatch.setattr(pvs, "_import_psycopg", lambda: fake_psycopg)

    pvs.retrieve_postgres_chunks(
        "question",
        filters={"category": "networking", "tags": ["vpn", "mfa"]},
        database_url="postgresql://fake",
        embedding_provider="hash",
    )

    cursor = fake_psycopg.connections[0].cursor()
    assert "d.category = ANY(%s)" in cursor.last_sql
    assert "d.tags && %s::text[]" in cursor.last_sql


def test_retrieve_postgres_chunks_ignores_unknown_filter_keys(monkeypatch) -> None:
    fake_psycopg = _FakePsycopg(rows=[])
    monkeypatch.setattr(pvs, "_import_psycopg", lambda: fake_psycopg)

    pvs.retrieve_postgres_chunks(
        "question",
        filters={"not_allowed": "x"},
        database_url="postgresql://fake",
        embedding_provider="hash",
    )

    cursor = fake_psycopg.connections[0].cursor()
    assert "not_allowed" not in cursor.last_sql


def test_retrieve_postgres_chunks_raises_and_logs_on_connection_failure(monkeypatch, caplog) -> None:
    fake_psycopg = _FakePsycopg(connect_error=ConnectionRefusedError("no db"))
    monkeypatch.setattr(pvs, "_import_psycopg", lambda: fake_psycopg)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(ConnectionRefusedError):
            pvs.retrieve_postgres_chunks(
                "question",
                database_url="postgresql://fake",
                embedding_provider="hash",
            )

    assert "Postgres hybrid retrieval failed" in caplog.text
