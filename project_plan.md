# Nexus (originally planned as "Enterprise Data & IT Knowledge RAG Assistant") — Project Plan

_This is the original planning document written before the product was named Nexus. Its
content is kept as a historical record of the initial blueprint and is not updated to
match later implementation decisions -- see `README.md` and `docs/architecture.md` for the
current, accurate state of the system._

## 1. Project Vision

The Enterprise Data & IT Knowledge RAG Assistant is a professional question-answering platform for IT, data engineering, security, and operations teams. It answers questions using trusted internal-style knowledge: tickets, runbooks, incident reports, onboarding pages, policies, architecture decisions, vendor documentation, Q&A records, and CVE data.

It solves a common enterprise problem: important operational knowledge is spread across many systems, often buried in long documents, old tickets, wiki pages, and incident notes. Engineers waste time searching, asking colleagues, or repeating previous investigations.

Target users:

- IT support engineers who need troubleshooting steps.
- Data engineers who need pipeline, data quality, and governance guidance.
- Security analysts who need CVE and incident context.
- New employees who need onboarding knowledge.
- Managers who want visibility into recurring issues and documentation gaps.

RAG is useful because it combines search over trusted documents with natural language answers. Compared with normal search, it synthesizes relevant context and cites sources. Compared with a normal chatbot, it grounds answers in retrieved evidence and can say "I do not know" when the knowledge base does not contain enough information.

## 2. Final System Features

### MVP Features

- Document ingestion from JSON, Markdown, PDF/text, CSV, and synthetic datasets.
- Document parsing and normalization.
- Chunking by document type.
- Embedding generation.
- Vector search with PostgreSQL + pgvector.
- FastAPI endpoint for question answering.
- Streamlit chat UI.
- Answers with source citations.
- "I do not know" behavior when retrieved context is weak or missing.
- Basic query logs.

### Professional Features

- Metadata filtering by category, department, access level, source type, date, and tags.
- Hybrid search using semantic vector search plus PostgreSQL full-text search.
- Reranking of retrieved chunks.
- Source citations with document title, chunk id, and excerpt.
- Query logs with latency, retrieved chunks, model used, and token/cost estimate.
- Feedback buttons: helpful, not helpful, wrong source, hallucinated, outdated.
- Evaluation dataset with expected answers and expected source chunks.
- RAG metrics: faithfulness, answer relevance, context precision, context recall, hallucination rate, latency, and cost.
- Admin dashboard for usage, quality, and ingestion monitoring.

### Advanced Features

- Query rewriting for vague, long, or multi-intent questions.
- Multi-step RAG for troubleshooting workflows.
- Document comparison, for example policy v1 vs v2.
- Incident assistant that summarizes incident history and recommends next actions.
- Security/CVE assistant using NVD records and internal vulnerability runbooks.
- Optional agentic RAG for tool use, ticket lookup, or guided workflows.
- Optional GraphRAG for relationships between systems, services, owners, incidents, and policies.

## 3. Dataset Strategy

Recommended first laptop dataset: about 500 to 1,200 documents and 3,000 to 10,000 chunks. This is realistic for PostgreSQL + pgvector on a normal laptop.

| Data source | Type of documents | Use in RAG system | Difficulty | Priority | Legal/privacy notes |
|---|---|---:|---:|---:|---|
| Synthetic IT tickets | Password, VPN, email, access, cloud, database, Docker, Kubernetes, network issues | Troubleshooting and recurring support questions | Low | High | Fully synthetic; no personal data |
| Synthetic runbooks | Step-by-step operational guides | Grounded procedural answers | Medium | High | Fully synthetic |
| Synthetic IT/data policies | Access, backup, retention, data quality, incident response | Policy and compliance questions | Medium | High | Fully synthetic |
| Synthetic incident reports | Outages, root cause, timeline, impact, prevention | Incident assistant and lessons learned | Medium | High | Fully synthetic |
| Synthetic onboarding/wiki pages | Team docs, service overview, environment setup | New employee assistant | Low | Medium | Fully synthetic |
| Stack Exchange subset | IT, DevOps, Linux, database Q&A | Public Q&A examples and retrieval diversity | Medium | Medium | Respect license attribution requirements |
| Hugging Face subsets | Dolly, SQuAD, possibly curated QA records | Evaluation and baseline QA experiments | Low | Low | Check dataset license |
| Vendor documentation subset | Docker, Kubernetes, Linux, PostgreSQL, cloud docs | Technical documentation retrieval | Medium | Medium | Respect terms, robots.txt, and attribution |
| NVD/CVE subset | CVE JSON records | Security assistant | Medium | Optional | Public data, preserve source metadata |

Initial dataset target:

- 150 synthetic IT tickets.
- 35 synthetic runbooks.
- 20 synthetic IT/data policies.
- 20 synthetic incident reports.
- 20 synthetic onboarding/wiki pages.
- 100 to 300 public Q&A items.
- 50 to 150 vendor documentation pages or sections.
- Optional: 200 to 500 CVE records for one ecosystem, such as PostgreSQL, Docker, Kubernetes, Linux, or OpenSSL.

## 4. Synthetic Data Generation Plan

Every generated document should follow this JSON shape:

```json
{
  "document_id": "string",
  "title": "string",
  "category": "string",
  "department": "string",
  "source_type": "ticket|runbook|policy|incident_report|wiki|adr|faq",
  "created_at": "YYYY-MM-DD",
  "version": "string",
  "access_level": "public|internal|restricted",
  "tags": ["string"],
  "content": "string",
  "expected_questions": ["string"],
  "expected_answer_sources": ["string"]
}
```

### IT Helpdesk Ticket Prompt

Generate 25 realistic enterprise IT helpdesk tickets as JSON lines. Topics must include VPN, password reset, MFA, email delivery, database access, cloud permissions, Docker build failure, Kubernetes pod crash, network DNS issue, and laptop onboarding. Each ticket must include symptoms, user impact, environment, troubleshooting steps already attempted, resolution, root cause when known, timestamps, priority, and tags. Avoid real company names and personal data. Include expected questions that a RAG system should answer from the ticket.

### Incident Report Prompt

Generate 10 realistic post-incident reports for an enterprise data/IT environment. Each report must include summary, timeline, affected systems, severity, customer/user impact, detection method, root cause, contributing factors, mitigation, permanent fix, prevention actions, owner team, and links represented as synthetic document references. Include expected questions and expected source sections.

### Runbook Prompt

Generate 10 operational runbooks for IT and data engineering teams. Each runbook must include purpose, scope, prerequisites, required permissions, step-by-step procedure, validation checks, rollback plan, escalation path, known errors, and related documents. Topics: VPN outage, failed Airflow DAG, PostgreSQL high CPU, Kubernetes CrashLoopBackOff, expired TLS certificate, failed backup, data quality alert, disk space alert, access request, and CVE patch response.

### Internal IT Policy Prompt

Generate 10 internal IT policies. Each policy must include objective, scope, responsibilities, rules, exceptions, approval process, review cycle, audit evidence, and consequences. Topics: password policy, MFA, privileged access, backup retention, device security, remote work, incident response, software installation, cloud access, and vendor access.

### Data Governance Prompt

Generate 10 data governance documents. Each document must include data ownership, data classification, quality checks, retention rules, lineage expectations, access approval, monitoring, incident handling, and examples. Topics: customer data, finance data, analytics tables, raw zones, curated zones, PII masking, schema changes, SLA definitions, data contracts, and dashboard certification.

### Architecture Decision Record Prompt

Generate 10 architecture decision records using this structure: status, context, decision, options considered, consequences, risks, implementation notes, owners, date, and related documents. Topics: PostgreSQL + pgvector selection, FastAPI backend, Streamlit MVP, hybrid search, reranking, Docker Compose, MinIO, Airflow, evaluation pipeline, and metadata access control.

### FAQ Prompt

Generate 20 internal FAQ pages for IT support and data engineering. Each page must contain 8 to 12 Q&A pairs with specific operational answers, escalation contacts as fake team names, system references, and limitations. Avoid generic advice.

### Evaluation Question Prompt

Generate 100 evaluation questions for the synthetic knowledge base. For each question, provide expected answer, expected document ids, expected chunk/section names, answer type, difficulty, required filters, and whether the correct behavior is to answer or say "I do not know."

## 5. Data Model

Use PostgreSQL with pgvector as the main database.

| Table | Purpose |
|---|---|
| users | Stores user identity, role, department, and access level for filtering and auditing |
| documents | One row per source document with title, type, category, owner, version, storage path, and status |
| document_metadata | Flexible key-value metadata for document-specific attributes |
| chunks | Text chunks derived from documents, including chunk index, text, token count, and section title |
| embeddings | Vector representation of chunks using pgvector, linked one-to-one or one-to-many with chunks |
| queries | User questions, filters, rewritten query, intent, timestamps, latency, and status |
| retrieved_contexts | Chunks retrieved for each query, including rank, score, retrieval method, and rerank score |
| answers | Final generated answer, confidence, cited chunks, model, token usage, and cost estimate |
| feedback | User feedback on answer quality, citations, helpfulness, and free-text comments |
| evaluation_questions | Test questions with expected answers, expected documents, and expected chunks |
| evaluation_results | Metric outputs for each experiment and retrieval configuration |

Core fields:

```sql
documents(document_id, title, category, department, source_type, created_at, version, access_level, tags, storage_path, checksum, ingestion_status)
chunks(chunk_id, document_id, chunk_index, section_title, content, token_count, metadata_json)
embeddings(embedding_id, chunk_id, model_name, embedding vector, created_at)
queries(query_id, user_id, question, rewritten_question, intent, filters_json, created_at, latency_ms)
retrieved_contexts(query_id, chunk_id, rank, vector_score, keyword_score, hybrid_score, rerank_score)
answers(answer_id, query_id, answer_text, confidence, limitations, model_name, prompt_version, tokens_in, tokens_out, cost_estimate)
feedback(feedback_id, answer_id, user_id, rating, issue_type, comment, created_at)
```

## 6. RAG Architecture

```text
                 +----------------------+
                 | Streamlit Frontend   |
                 | Chat + Admin Views   |
                 +----------+-----------+
                            |
                            v
                 +----------------------+
                 | FastAPI Backend      |
                 | Auth, QA, Feedback   |
                 +----------+-----------+
                            |
        +-------------------+-------------------+
        |                   |                   |
        v                   v                   v
+---------------+   +---------------+   +----------------+
| Retrieval     |   | Generation    |   | Evaluation     |
| Vector, FTS,  |   | Prompting,    |   | Test sets,     |
| Hybrid, Rank  |   | Citations     |   | RAG metrics    |
+-------+-------+   +-------+-------+   +--------+-------+
        |                   |                    |
        v                   v                    v
+---------------------------------------------------------+
| PostgreSQL + pgvector                                   |
| documents, chunks, embeddings, queries, answers, evals   |
+---------------------------------------------------------+
        ^
        |
+-------+-------------------------------------------------+
| Ingestion Pipeline                                      |
| parse -> clean -> chunk -> embed -> store -> validate    |
+-------+-------------------------------------------------+
        ^
        |
+-------------------+        +----------------------------+
| Local Files/MinIO |        | Public + Synthetic Sources |
+-------------------+        +----------------------------+
```

Recommended stack:

- Frontend: Streamlit first, React later.
- Backend: FastAPI.
- Database: PostgreSQL + pgvector.
- Object storage: local folder first, MinIO later.
- Ingestion: Python scripts first, Airflow later.
- Embeddings: start with a local sentence-transformers model or a hosted embedding API.
- LLM: hosted LLM for best answers, local LLM as optional offline mode.
- Evaluation: custom metrics first, optional Ragas later.
- Deployment: Docker Compose.

## 7. Ingestion Pipeline

Steps:

1. Load documents from `data/raw`.
2. Detect file type and source type.
3. Extract text using appropriate parsers.
4. Normalize whitespace, headings, lists, and code blocks.
5. Remove boilerplate while preserving technical instructions.
6. Validate required metadata.
7. Split text into chunks based on document type.
8. Add metadata to every chunk.
9. Generate embeddings.
10. Store document, chunks, embeddings, and ingestion logs.
11. Validate chunk count, empty chunks, duplicate documents, and embedding dimensions.
12. Log errors with recoverable status.

Recommended chunking:

| Document type | Chunk size | Overlap | Notes |
|---|---:|---:|---|
| Tickets | 300-500 tokens | 50 | Keep symptoms, cause, and resolution together |
| Runbooks | 500-800 tokens | 100 | Split by procedure sections |
| Policies | 600-900 tokens | 100 | Preserve clauses and exceptions |
| Vendor docs | 700-1,000 tokens | 120 | Split by headings |
| CVE records | 200-400 tokens | 0-50 | Usually structured and short |

## 8. Retrieval Pipeline

1. User asks a question.
2. Backend records user, role, department, and filters.
3. Intent detector classifies normal QA, troubleshooting, incident, security, summary, or comparison.
4. Query is rewritten if it is vague, long, or missing key technical terms.
5. Vector search retrieves semantic matches from pgvector.
6. Keyword search retrieves lexical matches from PostgreSQL full-text search.
7. Results are combined using weighted hybrid scoring.
8. Metadata filters enforce category, department, access level, dates, and source type.
9. Top candidates are reranked.
10. Final context is selected with diversity across documents.
11. Generator answers using only retrieved context.
12. API returns direct answer, sources, confidence, limitations, and next step.
13. Query, retrieved chunks, answer, latency, and feedback are logged.

Hallucination controls:

- Require citations for factual claims.
- Use a minimum retrieval score threshold.
- Use "I do not know" when sources are weak or missing.
- Instruct the model to answer only from context.
- Keep source excerpts visible.
- Evaluate faithfulness and expected source match.
- Track feedback issue type "unsupported answer."

## 9. Prompting Strategy

### Normal Q&A System Prompt

You are an enterprise IT and data knowledge assistant. Answer only using the provided context. If the context does not contain enough evidence, say that you do not know based on the available documents. Always include: direct answer, supporting sources, confidence level, limitations, and recommended next step when relevant.

### Troubleshooting Assistant Prompt

You are a troubleshooting assistant for enterprise IT and data engineering teams. Use only the provided tickets, runbooks, incidents, and documentation. Give likely cause, diagnostic checks, resolution steps, validation steps, escalation path, sources, confidence, limitations, and next action. Do not invent commands, credentials, owners, or system states.

### Incident Assistant Prompt

You are an incident response assistant. Use only the provided incident reports, runbooks, tickets, and policies. Summarize impact, timeline, suspected or confirmed root cause, mitigation, permanent fix, related incidents, sources, confidence, limitations, and recommended next step. If the evidence is incomplete, say what is missing.

### Security/CVE Assistant Prompt

You are a security knowledge assistant. Use only the provided CVE records, vendor documentation, policies, and internal runbooks. Explain affected component, severity, exploitability if available, recommended remediation, validation, sources, confidence, limitations, and next step. Do not exaggerate risk beyond the provided evidence.

### Summarization Prompt

Summarize the provided document context for an enterprise technical audience. Include key facts, decisions, procedures, risks, owners if available, sources, confidence, limitations, and recommended next step. Do not add external knowledge.

### Comparison Prompt

Compare the provided documents using only the context. Highlight differences in scope, requirements, procedures, risks, owners, dates, and version changes. Include sources for each difference, confidence, limitations, and recommended next step.

### I Do Not Know Prompt

If the retrieved context does not provide enough evidence to answer, respond: "I do not know based on the available documents." Then explain what information is missing, list any partially relevant sources, set confidence to low, and recommend where the user should look next.

## 10. Evaluation Strategy

Build 100-200 evaluation questions:

- 40 troubleshooting questions.
- 25 policy/governance questions.
- 20 incident questions.
- 15 onboarding/wiki questions.
- 15 vendor documentation questions.
- 10 security/CVE questions.
- 10 unanswerable questions.

Track:

- Answer relevance.
- Faithfulness to retrieved sources.
- Context precision.
- Context recall.
- Expected source hit rate.
- Hallucination rate.
- Citation correctness.
- Latency.
- Cost per query.
- User feedback score.

Compare four retrieval configurations:

| Experiment | Purpose |
|---|---|
| Vector only | Semantic baseline |
| Keyword only | Exact-match baseline |
| Hybrid search | Professional retrieval baseline |
| Hybrid + reranking | Best-quality target |

Success target for interview demo:

- Expected source hit rate above 75%.
- Faithfulness above 85%.
- Hallucination rate below 5-10% on answerable questions.
- Correct "I do not know" behavior on most unanswerable questions.
- Average latency acceptable for demo, ideally under 5 seconds.

## 11. Monitoring and Dashboard

Admin dashboard sections:

- Total documents by source type.
- Total chunks and average chunks per document.
- Total queries over time.
- Average and p95 latency.
- Top searched topics and tags.
- Failed or unanswered questions.
- Low-confidence answer rate.
- Hallucination risk indicators.
- Feedback score and issue categories.
- Retrieval quality from evaluation runs.
- Estimated token/API cost.
- Most cited documents.
- Documents never retrieved.
- Ingestion errors.
- Recent evaluation results.

## 12. Project Implementation Roadmap

| Phase | Objective | Tasks | Deliverables | Concepts learned | Difficulty | Success criteria |
|---|---|---|---|---|---|---|
| 1 | Data prep and setup | Create repo, Docker Compose, env config, sample docs | Running project skeleton | Project structure, config | Easy | App starts locally |
| 2 | Basic ingestion | Parse JSON/Markdown, chunk, embed, store | Ingestion CLI | ETL, metadata, embeddings | Medium | 100 docs ingested |
| 3 | Basic RAG API | Build `/ask`, retrieval, prompt, citations | FastAPI RAG endpoint | API design, grounding | Medium | Answers cite sources |
| 4 | UI prototype | Build Streamlit chat and source panel | Demo UI | UX, user workflows | Easy | User can ask questions |
| 5 | Hybrid + reranking | Add FTS, score fusion, reranker | Better retrieval module | Search, ranking | Hard | Better eval score than vector only |
| 6 | Evaluation | Add test set runner and metrics | Evaluation report | RAG quality measurement | Hard | Repeatable experiment results |
| 7 | Monitoring | Add admin dashboard and logs | Monitoring UI | Observability | Medium | Shows usage and quality stats |
| 8 | Docker deployment | Containerize API, UI, DB | Docker Compose demo | Deployment | Medium | One-command startup |
| 9 | Advanced features | Add incident/CVE/document comparison modes | Advanced assistant modes | Multi-step RAG | Hard | At least one advanced demo works |
| 10 | Documentation | README, diagrams, report, CV bullets | Professional portfolio package | Communication | Medium | Interview-ready repo |

## 13. Folder Structure

```text
enterprise-rag-assistant/
  app/
    streamlit_app.py
    pages/
  api/
    main.py
    routes/
    schemas/
    services/
  ingestion/
    loaders/
    parsers/
    chunking/
    embedding/
    pipelines/
  retrieval/
    vector_search.py
    keyword_search.py
    hybrid_search.py
    reranker.py
  generation/
    prompts/
    answer_generator.py
    citation_builder.py
  evaluation/
    datasets/
    metrics.py
    run_evaluation.py
    reports/
  monitoring/
    dashboard.py
    analytics.py
  database/
    migrations/
    schema.sql
    seed.sql
  data/
    raw/
    processed/
    synthetic/
    evaluation/
  notebooks/
  tests/
    unit/
    integration/
  docker/
    Dockerfile.api
    Dockerfile.app
  docs/
    architecture.md
    data_strategy.md
    evaluation_report.md
  docker-compose.yml
  README.md
  pyproject.toml
  .env.example
```

## 14. Tech Stack Recommendation

| Tool | Why use it |
|---|---|
| Python | Best ecosystem for data engineering, NLP, RAG, and evaluation |
| FastAPI | Professional backend API with typing and automatic docs |
| PostgreSQL | Reliable relational database for metadata, logs, evaluation, and users |
| pgvector | Stores embeddings inside PostgreSQL, simpler than adding a separate vector DB |
| Streamlit | Fast MVP UI for chat, citations, and dashboard |
| Docker Compose | Reproducible local deployment for API, UI, and database |
| sentence-transformers or hosted embeddings | Easy embeddings; local option controls cost |
| Optional LangChain/LlamaIndex | Useful for rapid prototyping, but keep core logic understandable |
| Optional Ragas | RAG evaluation metrics after custom baseline works |
| Optional MinIO | Object storage simulation for enterprise architecture |
| Optional Airflow | Professional scheduled ingestion once basic scripts work |

## 15. Professional Deliverables

- GitHub repository with clean commits.
- README with problem, architecture, setup, demo, and screenshots.
- Architecture diagram.
- Data documentation and synthetic data generation method.
- API documentation from FastAPI/OpenAPI.
- Evaluation report comparing retrieval methods.
- Demo video showing ingestion, chat, citations, feedback, and dashboard.
- Final report for PFA/internship.
- CV bullet points.
- LinkedIn project description.

Example CV bullets:

- Built an enterprise RAG assistant using FastAPI, PostgreSQL, pgvector, Streamlit, hybrid search, reranking, and grounded answer generation with citations.
- Designed synthetic and public-data ingestion pipelines for IT tickets, runbooks, policies, incident reports, vendor docs, and CVE records.
- Implemented RAG evaluation comparing vector search, keyword search, hybrid retrieval, and reranking using faithfulness, context precision, source hit rate, latency, and hallucination metrics.

## 16. Risk Management

| Risk | Solution |
|---|---|
| Bad retrieval | Use metadata, hybrid search, reranking, and evaluation |
| Hallucination | Require citations, thresholds, faithful prompts, and "I do not know" behavior |
| Poor chunking | Tune chunk size by document type and evaluate expected source hits |
| Huge datasets | Start small, batch ingestion, deduplicate, and index carefully |
| Expensive API calls | Use local embeddings, cache embeddings, limit context, log cost |
| Private data leakage | Use synthetic data first, anonymize real docs, enforce access levels |
| Irrelevant answers | Add filters, intent detection, and feedback loops |
| Slow latency | Add indexes, reduce rerank candidates, cache frequent queries |
| Poor evaluation | Create expected sources and unanswerable questions |
| Licensing issues | Use public data carefully, preserve attribution, respect terms and robots.txt |

## 17. Final Recommendation

### Best First Version to Build in 7 Days

Build a local RAG MVP with synthetic documents only:

- 100 tickets.
- 20 runbooks.
- 10 policies.
- 10 incident reports.
- PostgreSQL + pgvector.
- FastAPI `/ask`.
- Streamlit chat.
- Citations.
- Basic "I do not know" threshold.
- Simple query logging.

### Best Version for a PFA Interview

Show a professional system with:

- Public + synthetic data.
- Hybrid search.
- Reranking.
- Evaluation report.
- Admin dashboard.
- Docker Compose.
- Clear README and architecture diagram.
- Demo video.

### Best Advanced Version Later

Add:

- Incident assistant.
- Security/CVE assistant.
- Document comparison.
- Airflow ingestion.
- MinIO document storage.
- Optional GraphRAG for systems, owners, incidents, and policies.

### Exact Next 10 Tasks Starting Today

1. Create the GitHub repository and folder structure.
2. Write `README.md` with the project vision and target features.
3. Create the PostgreSQL + pgvector Docker Compose file.
4. Define the first database schema in `database/schema.sql`.
5. Generate 20 synthetic documents using the metadata schema.
6. Write a Python ingestion script for JSON documents.
7. Implement chunking for tickets and runbooks.
8. Generate embeddings and store them in pgvector.
9. Build a basic FastAPI `/ask` endpoint with vector search.
10. Build a Streamlit chat UI that displays answer, sources, confidence, and limitations.

