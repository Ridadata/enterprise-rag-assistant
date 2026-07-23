from database.settings import get_database_url, get_psycopg_dsn


def test_get_psycopg_dsn_strips_sqlalchemy_driver_suffix(monkeypatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://rag_user:rag_password@localhost:5432/enterprise_rag"
    )

    assert get_psycopg_dsn() == "postgresql://rag_user:rag_password@localhost:5432/enterprise_rag"
    # get_database_url() is unchanged -- it's the stored/display form, used by tooling
    # that does expect the SQLAlchemy-style dialect suffix.
    assert get_database_url() == "postgresql+psycopg://rag_user:rag_password@localhost:5432/enterprise_rag"


def test_get_psycopg_dsn_is_a_no_op_when_url_has_no_driver_suffix(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://rag_user:rag_password@localhost:5432/enterprise_rag")

    assert get_psycopg_dsn() == "postgresql://rag_user:rag_password@localhost:5432/enterprise_rag"
