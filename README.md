# Enterprise Data & IT Knowledge RAG Assistant

Professional RAG assistant for enterprise IT, data engineering, security, and operations knowledge. The system is designed to answer questions from trusted internal-style documents such as tickets, runbooks, incident reports, onboarding notes, policies, architecture decisions, vendor docs, and CVE records.

## Scope

This repository starts with a local MVP:

- Synthetic IT/data documents
- JSON ingestion pipeline
- Document chunking and metadata normalization
- PostgreSQL with pgvector
- FastAPI `/ask` endpoint
- Streamlit chat UI
- Source citations
- Basic "I do not know" behavior when evidence is weak
- Query and answer logging foundation

Later phases add hybrid search, reranking, evaluation metrics, feedback, admin monitoring, incident/CVE modes, and Dockerized demo deployment.

## Architecture

```text
Streamlit UI -> FastAPI API -> Retrieval -> Generation
                         |        |            |
                         v        v            v
                  PostgreSQL + pgvector + query logs
                         ^
                         |
              Ingestion: parse -> chunk -> embed -> store
```

## Repository Layout

```text
app/                  Streamlit app
api/                  FastAPI backend
ingestion/            Load, normalize, chunk, embed, store documents
retrieval/            Vector, keyword, and hybrid search modules
generation/           Prompting, answer generation, citations
evaluation/           Test questions and RAG metrics
monitoring/           Usage and quality analytics
database/             SQL schema and migrations
data/                 Raw, synthetic, processed, and evaluation data
docs/                 Architecture and project documentation
tests/                Unit and integration tests
docker/               Container build files
```

## Quick Start

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
   pip install -e ".[dev]"
   ```

4. Run the API:

   ```bash
   uvicorn api.main:app --reload
   ```

5. Run the UI:

   ```bash
   streamlit run app/streamlit_app.py
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

## Source Plan

The detailed project blueprint is kept in [project_plan.md](project_plan.md).

