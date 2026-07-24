from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://rag_user:rag_password@localhost:5432/enterprise_rag"
    embedding_provider: str = "sentence_transformers"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    # Ordered, comma-separated fallback chain (see generation/providers/chain.py):
    # "auto" first tries every real provider that has an API key configured, in a fixed
    # free-tier-friendly order (gemini, groq, openrouter, openai, ollama, anthropic),
    # falling back to "mock" (always succeeds) if none are configured or all fail --
    # zero-config installs still work, and adding just one API key activates it with no
    # other changes. Set this explicitly (e.g. "groq,gemini" or just "mock") to override
    # the order or restrict which providers are tried.
    llm_providers: str = "auto"
    # Retries exist for a genuinely transient blip (one rate-limited request in an
    # otherwise-healthy provider), not to keep hammering a provider that's currently
    # struggling -- the chain falling over to the next configured provider is the real
    # recovery mechanism for that, and it can't kick in until retries against the current
    # one are exhausted. Observed in practice: with Gemini's free tier under sustained
    # load (every attempt timing out, not just one), llm_max_retries=2 meant 3 full
    # timeouts -- most of a minute -- before Groq even got a chance to answer. Kept at 1
    # (an initial attempt plus one retry) so that worst case is bounded much tighter.
    llm_max_retries: int = 1
    llm_retry_base_delay: float = 0.5
    # Every provider SDK defaults to a much longer request timeout than a human waiting
    # on an answer should ever sit through; each provider's generate() call raises on any
    # exception (including a timeout), which the chain in generation/providers/chain.py
    # catches and retries/falls back on, so this just bounds how long a single attempt
    # takes before that kicks in. Worst case per provider is roughly
    # (llm_max_retries+1) * llm_timeout_seconds, and that stall repeats for every
    # provider in the chain that's currently unresponsive before a caller gets an
    # answer -- keep both settings low enough that the worst case across the whole
    # chain still lands well under a minute.
    llm_timeout_seconds: float = 10.0

    gemini_api_key: str = ""
    # "-latest" alias (rather than a dated model like "gemini-2.5-flash") so this doesn't
    # silently start 404ing again the next time Google retires a model version -- fast,
    # has a genuinely free tier, and strong enough for grounded QA over retrieved context,
    # which is why Gemini is the recommended default primary provider.
    gemini_model: str = "gemini-flash-latest"

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"

    # A local Ollama server needs no API key -- it isn't a hosted/billed service.
    ollama_model: str = "llama3.1"
    ollama_base_url: str = "http://localhost:11434/v1"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"
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

    # Second-stage reranking (retrieval/reranker.py): a cross-encoder scores each
    # (question, chunk) pair directly (no vector math), which is slower per-pair but far
    # more precise than the first-stage hybrid/keyword score at telling "actually answers
    # this question" apart from "shares some words with it" -- the main lever for keeping
    # follow-up questions from dragging in unrelated documents. Uses sentence-transformers,
    # already a dependency for embeddings, so this needs no new package.
    rerank_enabled: bool = True
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    # Retrieval over-fetches this many candidates (instead of just top_k) so the reranker
    # has a real pool to re-sort rather than rubber-stamping the first-stage order.
    rerank_candidate_pool: int = 20
    # Cross-encoder logits are sigmoid-normalized to [0,1] (see reranker.py) before this
    # floor is applied -- a second chance to drop a candidate that made the first-stage
    # cutoff on keyword/vector overlap alone but that the cross-encoder, which actually
    # weighs question against chunk semantically, doesn't consider relevant. Calibrated
    # empirically once real queries are running; 0.2 is a conservative starting point that
    # only drops clearly-irrelevant candidates.
    rerank_min_score: float = 0.2

    # Query rewriting (generation/query_rewriter.py): condenses a follow-up question plus
    # prior conversation turns into a standalone query *before* retrieval runs, so e.g. "is
    # there a workaround" after a question about VPN failures retrieves VPN documents, not
    # whatever "workaround" alone happens to match. Only triggers when history is
    # non-empty -- a first question is already standalone, so paying for an extra LLM call
    # on every single request would be pure latency with no benefit.
    query_rewrite_enabled: bool = True
    # Deliberately tight and non-retrying: this call sits in front of retrieval on every
    # follow-up, and its failure mode is graceful (fall back to the raw follow-up question
    # verbatim), so it should fail fast rather than eating the same retry/timeout budget as
    # the main answer generation call and doubling worst-case latency.
    query_rewrite_max_retries: int = 0
    query_rewrite_timeout_seconds: float = 6.0
    # How many of the most recent turns to include when rewriting/generating -- bounds
    # prompt size and token cost as a conversation grows long.
    max_history_turns: int = 6
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
