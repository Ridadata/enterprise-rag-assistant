import json
from pathlib import Path

from ingestion.pipelines import load_to_postgres as ltp


class _FakeCursor:
    def __init__(self, log: list[tuple[str, tuple]]) -> None:
        self._log = log

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def execute(self, sql: str, params: tuple = ()) -> None:
        self._log.append((" ".join(sql.split()), params))


class _FakeConnection:
    def __init__(self) -> None:
        self.log: list[tuple[str, tuple]] = []
        self.commits = 0
        self.rollbacks = 0

    def __enter__(self) -> "_FakeConnection":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self.log)

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class _FakeJsonb:
    def __init__(self, data) -> None:
        self.data = data


class _FakePsycopg:
    def __init__(self, connection: _FakeConnection) -> None:
        self._connection = connection

    def connect(self, database_url: str, **kwargs) -> _FakeConnection:
        return self._connection


def _patch_psycopg(monkeypatch, connection: _FakeConnection) -> None:
    fake_psycopg = _FakePsycopg(connection)
    monkeypatch.setattr(ltp, "_import_psycopg", lambda: (fake_psycopg, _FakeJsonb))


def _write_jsonl(tmp_path: Path, documents: list[dict]) -> Path:
    path = tmp_path / "docs.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for document in documents:
            handle.write(json.dumps(document) + "\n")
    return path


def _document(document_id: str, content: str = "Some ticket content about VPN access.") -> dict:
    return {
        "document_id": document_id,
        "title": f"Title {document_id}",
        "category": "networking",
        "department": "IT",
        "source_type": "ticket",
        "created_at": "2026-01-01",
        "version": "1.0",
        "access_level": "internal",
        "tags": ["vpn"],
        "content": content,
    }


def test_load_jsonl_to_postgres_commits_each_document_independently(monkeypatch, tmp_path) -> None:
    connection = _FakeConnection()
    _patch_psycopg(monkeypatch, connection)
    source_path = _write_jsonl(tmp_path, [_document("doc-1"), _document("doc-2")])

    result = ltp.load_jsonl_to_postgres(source_path, database_url="postgresql://fake")

    assert result["document_count"] == 2
    assert result["failed_documents"] == []
    assert result["duplicate_document_ids"] == []
    assert connection.commits == 2
    assert connection.rollbacks == 0


def test_load_jsonl_to_postgres_deletes_stale_chunks_before_reinserting(monkeypatch, tmp_path) -> None:
    connection = _FakeConnection()
    _patch_psycopg(monkeypatch, connection)
    source_path = _write_jsonl(tmp_path, [_document("doc-1")])

    ltp.load_jsonl_to_postgres(source_path, database_url="postgresql://fake")

    statements = [sql for sql, _params in connection.log]
    delete_index = next(i for i, sql in enumerate(statements) if sql.startswith("DELETE FROM chunks"))
    insert_index = next(i for i, sql in enumerate(statements) if sql.startswith("INSERT INTO chunks"))
    assert delete_index < insert_index


def test_load_jsonl_to_postgres_skips_duplicate_document_ids_in_same_file(monkeypatch, tmp_path) -> None:
    connection = _FakeConnection()
    _patch_psycopg(monkeypatch, connection)
    source_path = _write_jsonl(tmp_path, [_document("doc-1"), _document("doc-1")])

    result = ltp.load_jsonl_to_postgres(source_path, database_url="postgresql://fake")

    assert result["document_count"] == 1
    assert result["duplicate_document_ids"] == ["doc-1"]
    assert connection.commits == 1


def test_load_jsonl_to_postgres_skips_invalid_document_without_aborting_batch(monkeypatch, tmp_path) -> None:
    connection = _FakeConnection()
    _patch_psycopg(monkeypatch, connection)
    invalid_document = {"document_id": "bad-doc"}  # missing required fields
    source_path = _write_jsonl(tmp_path, [invalid_document, _document("doc-2")])

    result = ltp.load_jsonl_to_postgres(source_path, database_url="postgresql://fake")

    assert result["document_count"] == 1
    assert len(result["failed_documents"]) == 1
    assert result["failed_documents"][0]["document_id"] == "bad-doc"
    assert connection.commits == 1
    assert connection.rollbacks == 0  # invalid docs are caught before any DB work starts


def test_load_jsonl_to_postgres_rolls_back_and_reports_embedding_dimension_mismatch(
    monkeypatch, tmp_path
) -> None:
    connection = _FakeConnection()
    _patch_psycopg(monkeypatch, connection)

    class _BadProvider:
        model_name = "bad-model"
        dimension = 384

        @staticmethod
        def embed_text(text: str) -> list[float]:
            return [0.0] * 10  # wrong dimension

        @staticmethod
        def vector_to_pgvector(vector: list[float]) -> str:
            return "[]"

    monkeypatch.setattr(ltp, "get_embedding_provider", lambda provider=None: _BadProvider())
    source_path = _write_jsonl(tmp_path, [_document("doc-1")])

    result = ltp.load_jsonl_to_postgres(source_path, database_url="postgresql://fake")

    assert result["document_count"] == 0
    assert len(result["failed_documents"]) == 1
    assert "dimension" in result["failed_documents"][0]["error"]
    assert connection.commits == 0
    assert connection.rollbacks == 1


def test_load_jsonl_to_postgres_one_bad_document_does_not_block_others(monkeypatch, tmp_path) -> None:
    connection = _FakeConnection()
    _patch_psycopg(monkeypatch, connection)
    source_path = _write_jsonl(
        tmp_path,
        [_document("doc-1"), {"document_id": "bad-doc"}, _document("doc-3")],
    )

    result = ltp.load_jsonl_to_postgres(source_path, database_url="postgresql://fake")

    assert result["document_count"] == 2
    assert len(result["failed_documents"]) == 1
    assert connection.commits == 2
