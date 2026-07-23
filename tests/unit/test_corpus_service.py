import pytest

from api.services import corpus_service


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
    def __init__(self, connection: _FakeConnection | None = None, connect_error: Exception | None = None) -> None:
        self._connection = connection
        self._connect_error = connect_error

    def connect(self, database_url: str, connect_timeout: int | None = None) -> _FakeConnection:
        if self._connect_error:
            raise self._connect_error
        return self._connection


def test_get_corpus_summary_maps_counts_and_source_type_breakdown(monkeypatch) -> None:
    connection = _FakeConnection(
        results=[
            (115,),  # SELECT COUNT(*) FROM documents
            (312,),  # SELECT COUNT(*) FROM chunks
            [("ticket", 60), ("runbook", 35), ("policy", 20)],  # GROUP BY source_type
        ]
    )
    monkeypatch.setitem(__import__("sys").modules, "psycopg", _FakePsycopg(connection=connection))

    summary = corpus_service.get_corpus_summary(database_url="postgresql://fake")

    assert summary.document_count == 115
    assert summary.chunk_count == 312
    assert summary.source_types == {"ticket": 60, "runbook": 35, "policy": 20}


def test_get_corpus_summary_raises_corpus_unavailable_on_connection_failure(monkeypatch) -> None:
    fake_psycopg = _FakePsycopg(connect_error=ConnectionRefusedError("no db"))
    monkeypatch.setitem(__import__("sys").modules, "psycopg", fake_psycopg)

    with pytest.raises(corpus_service.CorpusUnavailable):
        corpus_service.get_corpus_summary(database_url="postgresql://fake")
