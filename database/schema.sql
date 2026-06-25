CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    department TEXT NOT NULL,
    access_level TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    department TEXT NOT NULL,
    source_type TEXT NOT NULL,
    created_at DATE NOT NULL,
    version TEXT NOT NULL,
    access_level TEXT NOT NULL,
    tags TEXT[] NOT NULL DEFAULT '{}',
    storage_path TEXT,
    checksum TEXT,
    ingestion_status TEXT NOT NULL DEFAULT 'pending',
    inserted_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS document_metadata (
    metadata_id BIGSERIAL PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    key TEXT NOT NULL,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    section_title TEXT,
    content TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    search_vector TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
);

CREATE TABLE IF NOT EXISTS embeddings (
    embedding_id BIGSERIAL PRIMARY KEY,
    chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id) ON DELETE CASCADE,
    model_name TEXT NOT NULL,
    embedding VECTOR(384) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS queries (
    query_id BIGSERIAL PRIMARY KEY,
    user_id TEXT,
    question TEXT NOT NULL,
    rewritten_question TEXT,
    intent TEXT,
    filters_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    latency_ms INTEGER,
    status TEXT NOT NULL DEFAULT 'started'
);

CREATE TABLE IF NOT EXISTS retrieved_contexts (
    query_id BIGINT NOT NULL REFERENCES queries(query_id) ON DELETE CASCADE,
    chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id) ON DELETE CASCADE,
    rank INTEGER NOT NULL,
    vector_score DOUBLE PRECISION,
    keyword_score DOUBLE PRECISION,
    hybrid_score DOUBLE PRECISION,
    rerank_score DOUBLE PRECISION,
    PRIMARY KEY (query_id, chunk_id)
);

CREATE TABLE IF NOT EXISTS answers (
    answer_id BIGSERIAL PRIMARY KEY,
    query_id BIGINT NOT NULL REFERENCES queries(query_id) ON DELETE CASCADE,
    answer_text TEXT NOT NULL,
    confidence TEXT NOT NULL,
    limitations TEXT,
    model_name TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    tokens_in INTEGER,
    tokens_out INTEGER,
    cost_estimate NUMERIC(12, 6),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS feedback (
    feedback_id BIGSERIAL PRIMARY KEY,
    answer_id BIGINT NOT NULL REFERENCES answers(answer_id) ON DELETE CASCADE,
    user_id TEXT,
    rating TEXT NOT NULL,
    issue_type TEXT,
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS evaluation_questions (
    evaluation_question_id BIGSERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    expected_answer TEXT,
    expected_document_ids TEXT[] NOT NULL DEFAULT '{}',
    expected_chunk_ids TEXT[] NOT NULL DEFAULT '{}',
    answer_type TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    required_filters JSONB NOT NULL DEFAULT '{}'::jsonb,
    should_answer BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS evaluation_results (
    evaluation_result_id BIGSERIAL PRIMARY KEY,
    experiment_name TEXT NOT NULL,
    evaluation_question_id BIGINT NOT NULL REFERENCES evaluation_questions(evaluation_question_id),
    answer_id BIGINT REFERENCES answers(answer_id),
    faithfulness DOUBLE PRECISION,
    answer_relevance DOUBLE PRECISION,
    context_precision DOUBLE PRECISION,
    context_recall DOUBLE PRECISION,
    hallucination_flag BOOLEAN,
    latency_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_documents_source_type ON documents(source_type);
CREATE INDEX IF NOT EXISTS idx_documents_access_level ON documents(access_level);
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_search_vector ON chunks USING GIN(search_vector);
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON embeddings USING ivfflat (embedding vector_cosine_ops);

