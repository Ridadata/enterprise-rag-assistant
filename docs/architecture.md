# Architecture

```text
Next.js UI (web/) --Route Handler proxy--> FastAPI (api/) --> retrieval/ --> generation/
      |                                        |                  |               |
      v                                        v                  v               v
 X-API-Key header (server-only)        api/security.py    postgres_vector_    llm_client.py
                                                            search.py (hybrid)  (mock/anthropic/openai)
                                                            or vector_search.py
                                                            (local keyword fallback)
                                                                   |
                                                                   v
                                                      PostgreSQL + pgvector
                                                 documents, chunks, embeddings,
                                                 queries, answers, retrieved_contexts
                                                                   ^
                                                                   |
                                           ingestion/pipelines/load_to_postgres.py
                                           parse -> validate -> chunk -> embed -> store
```

## Request flow

1. The Next.js UI (`web/`) sends a question from the browser to its own same-origin
   `/api/*` Route Handler, which attaches `X-API-Key` server-side (the key never reaches
   the client bundle) and forwards it to `POST /ask`. Any other client can call `/ask`
   directly with its own `X-API-Key`.
2. `api/security.py`'s `require_api_key` dependency rejects unauthenticated requests (401)
   before any retrieval/generation work happens.
3. `retrieval/vector_search.py::retrieve_relevant_chunks` dispatches on
   `RAG_RETRIEVAL_BACKEND` (`auto` by default): try `retrieval/postgres_vector_search.py`'s
   hybrid pgvector-cosine + PostgreSQL full-text-search fusion first; on failure, fall back
   to local in-memory keyword scoring over the synthetic JSONL corpus (logged as a
   warning), unless the backend is pinned to `postgres` (fails hard, no fallback).
4. `generation/answer_generator.py` builds a prompt from the retrieved chunks and calls
   `generation/llm_client.py`, which dispatches on `LLM_PROVIDER` (`mock` by default --
   deterministic extractive answer, no network/API key needed; `anthropic`/`openai` call a
   real model and gracefully fall back to the extractive answer on any failure).
5. `api/services/rag_service.py` logs the query, retrieved chunks, and answer
   (model/tokens/cost/confidence/latency) to Postgres -- best-effort; a logging failure
   never breaks the response.
6. The response includes the answer, confidence, limitations, next step, and source
   citations (document/chunk/excerpt/score).

## Supporting surfaces

- `GET /corpus/summary` -- document/chunk counts and source-type breakdown, read live from
  Postgres (not a re-parse of the JSONL file) for the Knowledge Base page (`web/app/(app)/knowledge`).
- `GET /admin/summary` -- usage/quality metrics (query volume, latency percentiles,
  confidence distribution, IDK rate, token/cost totals, most-cited and never-retrieved
  documents) computed from the `queries`/`answers`/`retrieved_contexts` tables, rendered by
  the Admin Analytics page (`web/app/(app)/admin`).
- Both admin/corpus endpoints sit behind the same `X-API-Key` dependency as `/ask`.

## Ingestion

`ingestion/pipelines/load_to_postgres.py` validates each document, computes a checksum,
chunks it with a per-source-type size/overlap profile
(`ingestion/chunking/simple_chunker.py`), embeds each chunk via the configured
`EMBEDDING_PROVIDER` (`sentence_transformers`/`all-MiniLM-L6-v2` by default, `hash` as a
fast/offline stub), and commits per-document so one bad or duplicate document is logged
and skipped rather than aborting the batch. Re-ingesting a document deletes its existing
chunks first (cascading to embeddings), so content that shrinks between runs doesn't leave
stale rows behind.

## Evaluation

`evaluation/run_evaluation.py` reuses each document's own `expected_questions` as a
ready-made eval set (the document itself is the expected retrieval hit), plus a fixed
unanswerable-question set for IDK testing, and reports hit rate, precision/recall@k, IDK
correctness, and latency for either backend -- see `docs/evaluation_report.md` for a real
run's results comparing local vs. hybrid retrieval.

## Deployment

`docker-compose.yml` runs all three services (`db`, `api`, `app`); `docker/Dockerfile.api`
and `docker/Dockerfile.app` build the backend and UI images respectively. The UI image is a
standalone Next.js server build (`output: "standalone"`) that only ever talks to the API
over HTTP -- it doesn't import any ingestion/retrieval/generation internals.

## Deliberately out of scope (for now)

Cross-encoder reranking, feedback capture (the `feedback` table exists but nothing writes
to it), an LLM-judge evaluation pass (faithfulness/hallucination scoring), and
incident/CVE/document-comparison assistant modes. See `project_plan.md` for the full
roadmap these were scoped against.
