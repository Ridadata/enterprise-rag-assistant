import "server-only";

/**
 * Server-only fetch to the FastAPI backend. Used exclusively inside app/api/*\/route.ts
 * handlers -- never import this from a client component. The X-API-Key is read from a
 * server-only env var (no NEXT_PUBLIC_ prefix) so it never reaches the client bundle.
 */

const BASE_URL = process.env.NEXUS_API_BASE_URL ?? "http://localhost:8000";
const API_KEY = process.env.NEXUS_API_KEY ?? "";

interface CallBackendOptions {
  method?: "GET" | "POST";
  body?: unknown;
  timeoutMs?: number;
  requireAuth?: boolean;
}

export async function callBackend(path: string, options: CallBackendOptions = {}): Promise<Response> {
  const { method = "GET", body, timeoutMs = 10_000, requireAuth = true } = options;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(`${BASE_URL}${path}`, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...(requireAuth ? { "X-API-Key": API_KEY } : {}),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: controller.signal,
      cache: "no-store",
    });
  } finally {
    clearTimeout(timeout);
  }
}
