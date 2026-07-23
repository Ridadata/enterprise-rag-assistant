# Evaluation Report

## Method

`evaluation/run_evaluation.py` builds its question set from the synthetic corpus's own
`expected_questions` field (each document already declares questions it should be able to
answer, per the synthetic data generation schema in `project_plan.md`) plus a fixed set of
5 deliberately unrelated questions to exercise the "I do not know" path. This run used 100
answerable questions (one per document, first 100 documents) + 5 unanswerable questions
= 105 total, evaluated against both retrieval backends with `top_k=5`.

Reproduce with:

```bash
python -m ingestion.pipelines.load_to_postgres data/synthetic/enterprise_knowledge_base.jsonl --reset
python -m evaluation.run_evaluation --corpus data/synthetic/enterprise_knowledge_base.jsonl --limit 100 --backend both --top-k 5
```

## Results

| Metric | Local (keyword) | Postgres (hybrid) |
|---|---:|---:|
| Expected-source hit rate | 49.0% | **91.0%** |
| Mean precision@5 | 0.098 | 0.183 |
| Mean recall@5 | 0.49 | 0.91 |
| "I do not know" correctness | 99.1% | 100% |
| Mean latency | 17.2 ms | 265.6 ms* |
| p95 latency | 25.3 ms | 92.4 ms |

\* Mean latency is skewed upward by the one-time sentence-transformers model load on the
first request in a fresh process (a few seconds); p95 is the more representative number
for steady-state request latency.

## Reading the numbers

- **Hybrid retrieval nearly doubles the hit rate** (49% -> 91%) over local keyword
  search. This is the core payoff of Tier 1's embedding/retrieval work: the local backend
  only matches on lexical term overlap, while the hybrid backend combines real
  `sentence-transformers/all-MiniLM-L6-v2` cosine similarity with PostgreSQL full-text
  search.
- **Precision@5 is low in absolute terms for both backends** (0.10-0.18) because each
  question in this set has exactly one "correct" source document but `top_k=5` chunks are
  requested -- at most 1/5 = 0.20 precision is achievable by construction. Recall (whether
  the correct document appears *anywhere* in the top 5) is the more meaningful number here,
  and hybrid's 0.91 means the right document is almost always retrieved somewhere in the
  candidate set.
- **"I do not know" correctness is high for both** (99-100%) -- both backends' retrieval
  thresholds (`MIN_RETRIEVAL_SCORE`, calibrated in `database/settings.py` against measured
  score distributions -- see that file's comment) correctly withhold an answer when nothing
  clears the bar.
- **p95 latency (92ms for hybrid) is comfortably within** `project_plan.md`'s demo target
  of "under 5 seconds," even before any caching.

## Not yet measured

Faithfulness, answer relevance, context precision/recall (in the RAGAS/LLM-judge sense),
and hallucination rate are **not** measured here -- they require an LLM-as-judge, which is
out of scope for this pass (`LLM_PROVIDER=mock` by default; see `generation/llm_client.py`
for the provider switch). `evaluation/metrics.py` implements only the deterministic
metrics (hit rate, precision/recall@k, IDK correctness, latency) that don't require a
judge model, per the scoping decision recorded when the harness was built. Wiring in a
real LLM provider and an LLM-judge pass would be the natural next step for a fuller
evaluation matching `project_plan.md`'s full metric list.
