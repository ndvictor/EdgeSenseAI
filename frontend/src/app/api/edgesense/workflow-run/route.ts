/**
 * NextAuth-gated proxy for the DeepAgents workflow RUN endpoint.
 *
 * Browser -> this Next.js route (NextAuth session required) -> Azure backend
 * `/api/v1/daytrading/workflow/run` with `X-Ops-Admin-Token` injected
 * server-side. The signed-in NextAuth email is forwarded as
 * `requested_by_email` so the workflow run record carries the operator.
 *
 * The browser sends `{ run_mode, symbols?, confirm_live?, confirm_live_phrase? }`.
 * All gate validation (paper gates on, live gates on, confirm_live_phrase
 * equals 'LIVE', etc.) is enforced by the backend; this route only forwards.
 */

import { NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";

import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const BACKEND_PATH = "/api/v1/daytrading/workflow/run";

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

export async function POST(req: NextRequest) {
  // Dev bypass: localhost runs without Google sign-in. Production keeps the
  // NextAuth gate so only signed-in owners reach the protected backend.
  let email: string | null;
  if (IS_DEV) {
    email = "dev@localhost";
  } else {
    const token = await getToken({ req, secret: process.env.NEXTAUTH_SECRET });
    if (!token) {
      return NextResponse.json({ status: "error", reason: "not_authenticated" }, { status: 401 });
    }
    email = (token.email || "").toString().trim() || null;
  }

  const base = backendBaseUrl();
  if (!base) {
    return NextResponse.json(
      { status: "error", reason: "backend_url_not_configured" },
      { status: 503 },
    );
  }
  const adminToken = opsToken();
  if (!adminToken) {
    return NextResponse.json(
      { status: "error", reason: "ops_admin_token_not_configured_on_frontend" },
      { status: 503 },
    );
  }

  let payload: Record<string, unknown>;
  try {
    payload = (await req.json()) as Record<string, unknown>;
  } catch {
    return NextResponse.json({ status: "error", reason: "invalid_json_body" }, { status: 400 });
  }

  const body = {
    ...payload,
    requested_by_email: email,
  };

  try {
    const upstream = await fetch(`${base}${BACKEND_PATH}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        "X-Ops-Admin-Token": adminToken,
        "X-Ops-Admin-Email": email ?? "",
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    const text = await upstream.text();
    let parsed: unknown;
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = { status: "error", reason: "invalid_backend_response", raw: text.slice(0, 500) };
    }
    return NextResponse.json(parsed, { status: upstream.status });
  } catch {
    return NextResponse.json({ status: "error", reason: "backend_unreachable" }, { status: 502 });
  }
}
