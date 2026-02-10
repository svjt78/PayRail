import { NextRequest, NextResponse } from "next/server";

const API = process.env.INTERNAL_API_URL || "http://api-gateway:8026";
const PROVIDER_SIM = process.env.PROVIDER_SIM_URL || "http://provider-sim:8028";

export async function GET() {
  const res = await fetch(`${API}/providers/health`, {
    cache: "no-store",
  });
  return NextResponse.json(await res.json(), { status: res.status });
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  const providerId = body.provider_id;
  if (!providerId) {
    return NextResponse.json({ error: "provider_id required" }, { status: 400 });
  }
  delete body.provider_id;

  const res = await fetch(`${PROVIDER_SIM}/providers/${providerId}/inject-failure`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return NextResponse.json(await res.json(), { status: res.status });
}
