/**
 * NextAuth-gated proxy for the trading gate config endpoints.
 *
 * Browser -> this Next.js route (NextAuth session required) -> Azure backend
 * with `X-Ops-Admin-Token` injected server-side. The OPS_ADMIN_TOKEN never
 * touches the browser. The signed-in NextAuth email is forwarded via
 * `X-Ops-Admin-Email` so the backend audit trail records the operator.
 *
 * GET  -> /api/v1/daytrading/settings/gates
 * PUT  -> /api/v1/daytrading/settings/gates
 */

import { NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";

import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const BACKEND_PATH = "/api/v1/daytrading/settings/gates";

function backendBaseUrl(): string | null {
  const raw =
    process.env.BACKEND_BASE_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "";
  const cleaned = raw.trim().replace(/\/+$/, "");
  return cleaned || null;
}

function opsToken(): string | null {
  const raw = process.env.OPS_ADMIN_TOKEN || "";
  return raw.trim() || null;
}

const IS_DEV = process.env.NODE_ENV !== "production";

async function requireSession(req: NextRequest): Promise<string | null> {
  // Dev bypass: on localhost we skip NextAuth so the panel works without Google
  // sign-in. Production (Vercel) still requires a real session.
  if (IS_DEV) {
    return "dev@localhost";
  }
  const token = await getToken({ req, secret: process.env.NEXTAUTH_SECRET });
  if (!token) return null;
  const email = (token.email || "").toString().trim();
  return email || null;
}

function backendDownResponse(reason: string): NextResponse {
  return NextResponse.json(
    { status: "error", reason },
    { status: 502 },
  );
}

export async function GET(req: NextRequest) {
  const email = await requireSession(req);
  if (!email) {
    return NextResponse.json({ status: "error", reason: "not_authenticated" }, { status: 401 });
  }
  const base = backendBaseUrl();
  if (!base) {
    return NextResponse.json(
      { status: "error", reason: "backend_url_not_configured" },
      { status: 503 },
    );
  }
  try {
    const upstream = await fetch(`${base}${BACKEND_PATH}`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    const text = await upstream.text();
    let body: unknown;
    try {
      body = JSON.parse(text);
    } catch {
      body = { status: "error", reason: "invalid_backend_response", raw: text.slice(0, 500) };
    }
    return NextResponse.json(body, { status: upstream.status });
  } catch {
    return backendDownResponse("backend_unreachable");
  }
}

export async function PUT(req: NextRequest) {
  const email = await requireSession(req);
  if (!email) {
    return NextResponse.json({ status: "error", reason: "not_authenticated" }, { status: 401 });
  }
  const base = backendBaseUrl();
  if (!base) {
    return NextResponse.json(
      { status: "error", reason: "backend_url_not_configured" },
      { status: 503 },
    );
  }
  const token = opsToken();
  if (!token) {
    return NextResponse.json(
      { status: "error", reason: "ops_admin_token_not_configured_on_frontend" },
      { status: 503 },
    );
  }

  let payload: unknown;
  try {
    payload = await req.json();
  } catch {
    return NextResponse.json({ status: "error", reason: "invalid_json_body" }, { status: 400 });
  }

  try {
    const upstream = await fetch(`${base}${BACKEND_PATH}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        "X-Ops-Admin-Token": token,
        "X-Ops-Admin-Email": email,
      },
      body: JSON.stringify(payload ?? {}),
      cache: "no-store",
    });
    const text = await upstream.text();
    let body: unknown;
    try {
      body = JSON.parse(text);
    } catch {
      body = { status: "error", reason: "invalid_backend_response", raw: text.slice(0, 500) };
    }
    return NextResponse.json(body, { status: upstream.status });
  } catch {
    return backendDownResponse("backend_unreachable");
  }
}
