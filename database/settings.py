from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://rag_user:rag_password@localhost:5432/enterprise_rag"
    embedding_provider: str = "sentence_transformers"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    llm_provider: str = "mock"
    llm_model: str = "mock-grounded-answer"
    # Both the Anthropic and OpenAI SDKs default to multi-minute request timeouts, far too
    # long for a request a human is waiting on; llm_client.py's generate() already falls
    # back to the extractive answer on any exception (including a timeout), so this just
    # bounds how long a caller waits before that fallback kicks in.
    llm_timeout_seconds: float = 30.0
    # Calibrated against real sentence-transformer embeddings (see retrieve_postgres_chunks):
    # raw cosine similarity between *unrelated* English sentences typically sits ~0.4-0.5
    # after the (-1,1)->(0,1) rescale, so a threshold tuned for the old Jaccard-overlap
    # scorer (which hits exactly 0 for unrelated text) let obviously irrelevant chunks
    # through. 0.5 separates measured relevant (~0.52-0.67) from unrelated (~0.39-0.50)
    # hybrid scores, and the local keyword backend's own relevant-query scores (~0.58-1.0)
    # clear it comfortably too.
    min_retrieval_score: float = 0.5
    # "auto" tries the postgres hybrid backend first and falls back to local keyword search
    # (with a logged warning) if postgres is unreachable -- "postgres" fails hard, "local"
    # never tries postgres at all.
    rag_retrieval_backend: str = "auto"
    # Comma-separated shared API keys accepted by protected endpoints (/ask, /corpus/summary,
    # /admin/*). Empty by default so a missing .env fails closed (401) rather than silently
    # running the API wide open.
    api_keys: str = ""

    def allowed_api_keys(self) -> frozenset[str]:
        return frozenset(key.strip() for key in self.api_keys.split(",") if key.strip())


def get_settings() -> Settings:
    """Re-read env/.env on every call so tests and callers can monkeypatch env vars freely."""
    return Settings()


def get_database_url() -> str:
    """DATABASE_URL in its stored (SQLAlchemy-style) form, e.g. for tooling/display."""
    return get_settings().database_url


def get_psycopg_dsn() -> str:
    """DATABASE_URL adapted for the raw psycopg driver.

    psycopg.connect() (unlike SQLAlchemy) doesn't understand a "+driver" dialect suffix
    in the URL scheme, so "postgresql+psycopg://..." must be normalized to "postgresql://..."
    before being passed to it.
    """
    return get_settings().database_url.replace("postgresql+psycopg://", "postgresql://", 1)
