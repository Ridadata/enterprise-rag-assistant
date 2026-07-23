# Data Strategy

The first project-ready dataset is synthetic and safe to publish. It mirrors internal enterprise knowledge without using real employees, companies, credentials, hosts, or ticket data.

## Current Corpus

The main corpus is `data/synthetic/enterprise_knowledge_base.jsonl`. It contains generated documents across:

- IT support tickets
- Operational runbooks
- Security and data policies
- Incident reports
- Onboarding/wiki pages
- Architecture decision records
- FAQ pages

The smaller `data/synthetic/sample_documents.jsonl` remains for compact tests and ingestion examples.

## Ingestion Stages

1. Source JSONL documents live in `data/synthetic/`.
2. `ingestion.pipelines.ingest_jsonl` validates metadata and splits documents into chunks.
3. `ingestion.embedding.hash_embedding` creates deterministic 384-dimensional embeddings for local development.
4. `ingestion.pipelines.load_to_postgres` can load documents, chunks, and embeddings into PostgreSQL + pgvector.
5. Retrieval can run in local JSONL mode or PostgreSQL mode.

## Backend Modes

Use local JSONL retrieval:

```powershell
$env:RAG_RETRIEVAL_BACKEND="local"
```

Use PostgreSQL + pgvector retrieval:

```powershell
$env:RAG_RETRIEVAL_BACKEND="postgres"
docker compose up -d db
.\.venv\Scripts\python.exe -m ingestion.pipelines.load_to_postgres data\synthetic\enterprise_knowledge_base.jsonl --reset
```

Use automatic fallback to local JSONL if PostgreSQL is unavailable:

```powershell
$env:RAG_RETRIEVAL_BACKEND="auto"
```

