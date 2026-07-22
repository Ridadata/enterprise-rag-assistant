import { NextResponse } from "next/server";
import { callBackend } from "@/lib/server-api";

export async function GET() {
  try {
    // /health has no auth dependency in the FastAPI app -- requireAuth is skipped here too.
    const response = await callBackend("/health", { timeoutMs: 5_000, requireAuth: false });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json({ status: "unreachable" }, { status: 502 });
  }
}
