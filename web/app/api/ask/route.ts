import { NextRequest, NextResponse } from "next/server";
import { callBackend } from "@/lib/server-api";

export async function POST(request: NextRequest) {
  const body = await request.json();

  try {
    const response = await callBackend("/ask", { method: "POST", body, timeoutMs: 30_000 });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json(
      { detail: "Can't reach the Nexus API. Is it running?" },
      { status: 502 },
    );
  }
}
