import type {
  AdminSummary,
  ApiResult,
  AskRequest,
  AskResponse,
  CorpusSummary,
} from "@/lib/types";

async function parse<T>(response: Response): Promise<ApiResult<T>> {
  if (response.ok) {
    const data = (await response.json()) as T;
    return { ok: true, data };
  }

  let message = "Something went wrong. Please try again.";
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") {
      message = body.detail;
    }
  } catch {
    // Response body wasn't JSON -- keep the default message.
  }

  const status = ([401, 422, 503, 500, 502] as const).includes(response.status as never)
    ? (response.status as 401 | 422 | 503 | 500 | 502)
    : 500;
  return { ok: false, status, message };
}

export async function askQuestion(payload: AskRequest): Promise<ApiResult<AskResponse>> {
  const response = await fetch("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parse<AskResponse>(response);
}

export async function getCorpusSummary(): Promise<ApiResult<CorpusSummary>> {
  const response = await fetch("/api/corpus/summary");
  return parse<CorpusSummary>(response);
}

export async function getAdminSummary(): Promise<ApiResult<AdminSummary>> {
  const response = await fetch("/api/admin/summary");
  return parse<AdminSummary>(response);
}

export async function getHealth(): Promise<ApiResult<{ status: string }>> {
  const response = await fetch("/api/health");
  return parse<{ status: string }>(response);
}
