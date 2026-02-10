import { NextRequest, NextResponse } from "next/server";

const API = process.env.INTERNAL_API_URL || "http://api-gateway:8026";

export async function GET(request: NextRequest) {
  const params = request.nextUrl.searchParams.toString();
  const res = await fetch(`${API}/payment-intents?${params}`, {
    headers: { "X-Merchant-Id": "m_001", "X-Role": "operator" },
    cache: "no-store",
  });
  return NextResponse.json(await res.json(), { status: res.status });
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  const res = await fetch(`${API}/payment-intents`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Merchant-Id": "m_001",
      "X-Role": "operator",
      "Idempotency-Key": body.idempotency_key || crypto.randomUUID(),
    },
    body: JSON.stringify(body),
  });
  return NextResponse.json(await res.json(), { status: res.status });
}
