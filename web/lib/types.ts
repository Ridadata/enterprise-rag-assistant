/**
 * Mirrors api/schemas/*.py 1:1. Keep these in sync by hand -- there's no shared codegen
 * between the FastAPI backend and this frontend.
 */

export type ConfidenceLevel = "high" | "medium" | "low";

export type FilterKey = "category" | "department" | "source_type" | "access_level" | "tags";

export const ALLOWED_FILTER_KEYS: FilterKey[] = [
  "category",
  "department",
  "source_type",
  "access_level",
  "tags",
];

export interface AskRequest {
  question: string;
  user_id?: string;
  filters?: Partial<Record<FilterKey, string | string[]>>;
}

export interface SourceCitation {
  document_id: string;
  title: string;
  chunk_id: string;
  excerpt: string;
  score: number;
}

export interface AskResponse {
  answer: string;
  confidence: ConfidenceLevel;
  limitations: string;
  next_step: string;
  sources: SourceCitation[];
  latency_ms: number;
  model_name: string;
}

export interface CorpusSummary {
  document_count: number;
  chunk_count: number;
  source_types: Record<string, number>;
}

export interface QueryVolumePoint {
  day: string; // YYYY-MM-DD
  query_count: number;
}

export interface CitedDocument {
  document_id: string;
  title: string;
  citation_count: number;
}

export interface IngestionStatusCount {
  status: string;
  count: number;
}

export interface AdminSummary {
  retrieval_backend: string;
  total_queries: number;
  mean_latency_ms: number | null;
  p95_latency_ms: number | null;
  confidence_counts: Record<string, number>;
  idk_rate: number;
  total_tokens_in: number;
  total_tokens_out: number;
  total_cost_estimate: number;
  queries_by_day: QueryVolumePoint[];
  most_cited_documents: CitedDocument[];
  never_retrieved_document_count: number;
  ingestion_status_counts: IngestionStatusCount[];
  most_recent_ingestion_at: string | null; // ISO datetime
}

/** Discriminated shape returned by every /api/* route handler -- see lib/server-api.ts. */
export type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; status: 401 | 422 | 503 | 500 | 502; message: string };
