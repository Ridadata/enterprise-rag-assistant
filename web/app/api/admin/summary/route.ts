import { NextResponse } from "next/server";
import { callBackend } from "@/lib/server-api";

export async function GET() {
  try {
    const response = await callBackend("/admin/summary");
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json(
      { detail: "Can't reach the Nexus API. Is it running?" },
      { status: 502 },
    );
  }
}
