# Nexus

**Enterprise Knowledge Platform** — grounded question answering over enterprise IT and data knowledge, with citations, confidence scoring, and a live analytics dashboard.

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688)
![Next.js](https://img.shields.io/badge/Next.js-UI-000000)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-336791)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED)
![License](https://img.shields.io/badge/license-MIT-green)

Nexus answers questions from trusted internal-style documents — tickets, runbooks, incident reports, onboarding notes, policies, architecture decisions, vendor docs, and CVE records — and grounds every answer in retrieved evidence rather than free-form generation.

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Repository Layout](#repository-layout)
- [Data](#data)
- [Quick Start](#quick-start)
- [Screenshots](#screenshots)
- [Development Checks](#development-checks)
- [Current Milestone](#current-milestone)
- [License](#license)

## Features

- **Grounded, cited answers** with a per-source match-confidence score, not just a raw model completion.
- **Hybrid retrieval** — real sentence-transformer embeddings (pgvector cosine similarity) fused with PostgreSQL full-text search, with an automatic local-keyword fallback if the database is unreachable.
- **Honest "I don't know" behavior** when retrieved evidence is too weak to support an answer, instead of guessing.
- **Live admin dashboard** — query volume, latency percentiles, confidence distribution, ingestion status, and most-cited/never-retrieved documents, all computed from real logged data.
- **API-key authenticated backend** — every endpoint (`/ask`, `/corpus/summary`, `/admin/summary`) requires a valid key.
- **Evaluation harness** comparing retrieval backends on expected-source hit rate, precision/recall@k, and latency — see [`docs/evaluation_report.md`](docs/evaluation_report.md) for a real run's results.
- **One-command Docker deployment** for the full stack (database, API, UI).

## Architecture

```text
Next.js UI -> FastAPI API -> Retrieval -> Generation
                         |        |            |
                         v        v            v
                  PostgreSQL + pgvector + query logs
                         ^
                         |
              Ingestion: parse -> chunk -> embed -> store
```

See [`docs/architecture.md`](docs/architecture.md) for the full request flow, including auth, the retrieval-backend fallback chain, and the admin/corpus API surfaces.

## Repository Layout

```text
web/                  Next.js UI (search/chat, knowledge base, admin analytics, settings)
api/                  FastAPI backend
ingestion/            Load, normalize, chunk, embed, store documents
retrieval/            Vector, keyword, and hybrid search modules
generation/           Prompting, answer generation, citations
evaluation/           Test questions and RAG metrics
monitoring/           Usage and quality analytics
database/             SQL schema and settings
data/                 Raw, synthetic, processed, and evaluation data
docs/                 Architecture and evaluation documentation
tests/                Unit and integration tests
docker/               Container build files
```

## Data

The current project data is synthetic and lives in:

- `data/synthetic/enterprise_knowledge_base.jsonl`: main generated demo corpus with 115 documents.
- `data/synthetic/sample_documents.jsonl`: compact curated sample for tests and examples.
- `data/processed/sample_chunks.jsonl`: processed chunk preview with local deterministic embeddings.

Generate or refresh the main corpus:

```bash
python scripts/generate_synthetic_data.py --output data/synthetic/enterprise_knowledge_base.jsonl
```

Export processed chunks:

```bash
python -m ingestion.pipelines.ingest_jsonl data/synthetic/sample_documents.jsonl --processed-output data/processed/sample_chunks.jsonl --with-embeddings
```

See [data/README.md](data/README.md) and [docs/data_strategy.md](docs/data_strategy.md) for details.

## Quick Start

### Option A: Docker (full stack)

```bash
cp .env.example .env
docker compose up -d
python -m ingestion.pipelines.load_to_postgres data/synthetic/enterprise_knowledge_base.jsonl --reset
```

This brings up Postgres+pgvector (port 5433), the FastAPI backend (port 8000), and the
Next.js UI (port 3000). The ingestion step needs to be run once against the containerized
`db` service, e.g. `docker compose exec api python -m ingestion.pipelines.load_to_postgres ...`
or from the host once `.env`'s `DATABASE_URL` resolves to it.

### Option B: Local Python + containerized Postgres only

1. Copy environment variables:

   ```bash
   cp .env.example .env
   ```

2. Start PostgreSQL with pgvector:

   ```bash
   docker compose up -d db
   ```

3. Install Python dependencies:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -e ".[dev,embeddings]"
   ```

4. Run the API:

   ```bash
   uvicorn api.main:app --reload
   ```

5. Run the UI:

   ```bash
   cd web
   npm install
   cp .env.local.example .env.local
   npm run dev
   ```

> **Note (Windows):** if port 5432 is already in use by a native PostgreSQL install, this
> project maps the container to host port 5433 instead (see `docker-compose.yml`/`.env`).

Every API endpoint requires an `X-API-Key` header matching one of the comma-separated
values in `API_KEYS` (`.env`); the Next.js app's server-side proxy reads its own key from
`NEXUS_API_KEY` (`web/.env.local`) — both default to `dev-demo-key` locally.

## Screenshots

_Screenshots will be added here — see [Quick Start](#quick-start) above to view the app live at `http://localhost:3000`._

## Development Checks

Run the current local checks:

```bash
python -m pytest -q
python -m compileall api ingestion retrieval generation tests
ruff check .
```

Preview the synthetic JSONL ingestion without writing to the database:

```bash
python -m ingestion.pipelines.ingest_jsonl data/synthetic/sample_documents.jsonl
```

By default (`RAG_RETRIEVAL_BACKEND=auto`), `/ask` tries PostgreSQL + pgvector hybrid retrieval (real sentence-transformer embeddings + full-text search) first, falling back to local keyword search over `data/synthetic/enterprise_knowledge_base.jsonl` (with a logged warning) if Postgres isn't reachable. The answer generator is extractive by default (`LLM_PROVIDER=mock`); a real LLM provider can be wired in behind that same setting.

Load the generated corpus into PostgreSQL + pgvector:

```bash
docker compose up -d db
python -m ingestion.pipelines.load_to_postgres data/synthetic/enterprise_knowledge_base.jsonl --reset
```

Switch retrieval backend:

```bash
# try PostgreSQL hybrid search, fall back to local JSONL keyword search -- default
set RAG_RETRIEVAL_BACKEND=auto

# PostgreSQL + pgvector only (fails hard, no fallback)
set RAG_RETRIEVAL_BACKEND=postgres

# local JSONL keyword search only
set RAG_RETRIEVAL_BACKEND=local
```

Compare retrieval backends with the evaluation harness:

```bash
python -m evaluation.run_evaluation --backend both
```

## Current Milestone

The first milestone is a working vertical slice:

1. Load synthetic JSONL documents from `data/synthetic`.
2. Validate metadata and content.
3. Chunk documents by source type.
4. Store documents and chunks in PostgreSQL.
5. Add embeddings with pgvector.
6. Retrieve relevant chunks for a user question.
7. Generate a grounded answer with citations.
8. Log the query, retrieved chunks, answer, latency, and confidence.

The original project blueprint (written before the product was named Nexus) is kept for
historical reference in [project_plan.md](project_plan.md).

## License

MIT — see [LICENSE](LICENSE).
