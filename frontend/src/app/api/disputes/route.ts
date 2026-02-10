import { NextRequest, NextResponse } from "next/server";

const API = process.env.INTERNAL_API_URL || "http://api-gateway:8026";

export async function GET(request: NextRequest) {
  const params = request.nextUrl.searchParams.toString();
  const res = await fetch(`${API}/disputes?${params}`, {
    headers: { "X-Merchant-Id": "m_001" },
    cache: "no-store",
  });
  return NextResponse.json(await res.json(), { status: res.status });
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  const action = body._action;
  delete body._action;

  let url = `${API}/disputes`;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Merchant-Id": "m_001",
    "X-Role": "operator",
    "Idempotency-Key": body.idempotency_key || crypto.randomUUID(),
  };

  if (action === "submit-evidence") {
    url = `${API}/disputes/${body.dispute_id}/submit-evidence`;
    delete body.dispute_id;
  } else if (action === "resolve") {
    url = `${API}/disputes/${body.dispute_id}/resolve`;
    delete body.dispute_id;
  }

  const res = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  return NextResponse.json(await res.json(), { status: res.status });
}
