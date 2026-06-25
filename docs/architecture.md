# Architecture

The assistant follows a standard grounded RAG flow:

1. Ingest trusted documents.
2. Normalize metadata and text.
3. Chunk content by document type.
4. Generate embeddings.
5. Store documents, chunks, embeddings, logs, answers, and evaluation data in PostgreSQL.
6. Retrieve candidate chunks with vector search, then later with hybrid search and reranking.
7. Generate answers only from retrieved context.
8. Return citations, confidence, limitations, and a next step.

The MVP keeps the implementation deliberately small. The first production-style expansion should add hybrid retrieval and evaluation before adding advanced assistant modes.

