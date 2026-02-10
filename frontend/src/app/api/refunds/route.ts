import { NextRequest, NextResponse } from "next/server";

const API = process.env.INTERNAL_API_URL || "http://api-gateway:8026";

export async function GET(request: NextRequest) {
  const params = request.nextUrl.searchParams.toString();
  const res = await fetch(`${API}/refunds?${params}`, {
    headers: { "X-Merchant-Id": "m_001", "X-Role": "operator" },
    cache: "no-store",
  });
  return NextResponse.json(await res.json(), { status: res.status });
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  const action = body._action;
  delete body._action;

  let url = `${API}/refunds`;
  let headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Merchant-Id": body._merchant_id || "m_001",
    "X-Role": body._role || "operator",
    "Idempotency-Key": body.idempotency_key || crypto.randomUUID(),
  };
  delete body._merchant_id;
  delete body._role;

  if (action === "approve") {
    url = `${API}/refunds/${body.refund_id}/approve`;
    headers["X-Merchant-Id"] = "m_002";
    headers["X-Role"] = "approver";
    delete body.refund_id;
  } else if (action === "reject") {
    url = `${API}/refunds/${body.refund_id}/reject`;
    delete body.refund_id;
  }

  const res = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  return NextResponse.json(await res.json(), { status: res.status });
}
