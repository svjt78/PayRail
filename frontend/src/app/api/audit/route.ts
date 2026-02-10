import { NextRequest, NextResponse } from "next/server";

const API = process.env.INTERNAL_API_URL || "http://api-gateway:8026";

export async function GET(request: NextRequest) {
  const type = request.nextUrl.searchParams.get("type") || "payments";
  const limit = request.nextUrl.searchParams.get("limit") || "100";
  const res = await fetch(`${API}/audit/${type}?limit=${limit}`, {
    headers: { "X-Merchant-Id": "m_001" },
    cache: "no-store",
  });
  return NextResponse.json(await res.json(), { status: res.status });
}
