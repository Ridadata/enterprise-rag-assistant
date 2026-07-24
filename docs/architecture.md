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
3. If the request carries prior turns (`AskRequest.history`), `generation/query_rewriter.py`
   first checks a cheap, deterministic heuristic (`_looks_like_a_followup`: short question,
   or contains a pronoun/reference marker) before ever calling an LLM -- a self-contained
   new question skips rewriting entirely, so it can't be contaminated by an unrelated
   earlier topic. Only a question that actually looks like a follow-up gets condensed
   against the history into a standalone query, with a tight, non-retrying timeout budget
   (`QUERY_REWRITE_*`) so a slow rewrite call can't double the latency of every follow-up.
4. `retrieval/vector_search.py::retrieve_relevant_chunks` runs that (possibly rewritten)
   query against `RAG_RETRIEVAL_BACKEND` (`auto` by default): try
   `retrieval/postgres_vector_search.py`'s hybrid pgvector-cosine + PostgreSQL
   full-text-search fusion first; on failure, fall back to local in-memory keyword scoring
   over the synthetic JSONL corpus (logged as a warning), unless the backend is pinned to
   `postgres` (fails hard, no fallback). If `RERANK_ENABLED` (default), it over-fetches a
   larger candidate pool and hands it to `retrieval/reranker.py`, which re-scores every
   (question, chunk) pair with a cross-encoder and keeps only the top-k above
   `RERANK_MIN_SCORE` -- a second, more precise pass than the first-stage vector/keyword
   score, and the main reason a follow-up's retrieval stays on-topic.
5. `generation/answer_generator.py` builds a prompt from the retrieved chunks (plus recent
   history, so the model can resolve "it"/"that" naturally) and calls
   `generation/llm_client.py::generate()`, which resolves `LLM_PROVIDERS` (`auto` by
   default) into an ordered `ProviderChain` (`generation/providers/chain.py`) and tries
   each provider in turn: transient failures (rate limits, timeouts, 5xxs) are retried
   with exponential backoff (honoring a `Retry-After` header when the provider sends
   one) before moving to the next provider; a non-retryable failure (bad key, invalid
   model) skips straight to the next one. `auto` order is Gemini → Groq → OpenRouter →
   OpenAI → Anthropic, each included only if its API key is set, and the chain always
   ends in a deterministic mock provider that echoes the extractive fallback answer --
   so a fresh install with zero keys configured, or every real provider failing at
   once, both degrade to that same extractive answer rather than an error. OpenAI,
   Groq, OpenRouter, and a local Ollama server all share one implementation
   (`OpenAICompatibleProvider`) since they speak the same wire format; Gemini and
   Anthropic each have their own SDK-based provider. `generate_stream()` is the
   token-streaming counterpart, used by nothing yet in this codebase but available for
   a future streaming endpoint -- see each provider's `generate_stream()` and
   `ProviderChain.generate_stream()` for how retries interact with an in-progress
   stream (only before the first chunk; a mid-stream failure propagates directly).
6. `api/services/rag_service.py` logs the query, retrieved chunks, and answer
   (model/tokens/cost/confidence/latency) to Postgres -- best-effort; a logging failure
   never breaks the response.
7. The response includes the answer, confidence (derived from the top reranked score, not
   LLM self-assessment), limitations, next step, up to 3 LLM-suggested follow-up questions
   (parsed from the same generation call via a `FOLLOW_UP_QUESTIONS: [...]` marker in the
   prompt -- see `qa_system_prompt.txt` -- rather than a second round-trip), the actual
   `retrieval_query` used (useful for seeing what a rewrite produced), and source citations
   (document, chunk position, full chunk content, score).

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

Before that per-document work starts, it fetches the checksum already stored for every
document and the set of document IDs that already have embeddings under the currently
configured model (two bulk queries, not one per document) and skips a document entirely
-- no re-chunking, no re-embedding, no write -- when its checksum still matches and it's
already embedded under the current model. This is why re-running the script (e.g. on
every app startup, as opposed to once after the corpus actually changes) doesn't
redundantly rebuild the whole index: only new documents, documents whose content
changed, or documents never embedded under a newly-switched `EMBEDDING_PROVIDER` do real
work. `--reset` truncates everything first, so it naturally bypasses this and forces a
full rebuild.

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

Feedback capture (the `feedback` table exists but nothing writes to it), an LLM-judge
evaluation pass (faithfulness/hallucination scoring), persisted/resumable conversation
history (today's history is client-sent per request, not stored server-side -- see
`ConversationTurn` in `api/schemas/qa.py`), and incident/CVE/document-comparison assistant
modes. See `project_plan.md` for the full roadmap these were scoped against.
