import { NextRequest, NextResponse } from "next/server";

const API = process.env.INTERNAL_API_URL || "http://api-gateway:8026";

export async function GET() {
  const res = await fetch(`${API}/audit/reconciliation`, {
    headers: { "X-Merchant-Id": "m_001" },
    cache: "no-store",
  });
  return NextResponse.json(await res.json(), { status: res.status });
}
