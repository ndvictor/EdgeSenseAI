import { NextResponse } from "next/server";
import { withAuth } from "next-auth/middleware";

/**
 * Auth gate for the entire app.
 *
 * Next.js replaced the `middleware.ts` convention with `proxy.ts`. Keep this
 * auth boundary equivalent to the old middleware while exporting the proxy
 * function name expected by current Next dev builds.
 *
 * Dev bypass: when `NODE_ENV !== "production"` (i.e. `next dev` on
 * localhost:3900) the proxy is a no-op so we can iterate without Google
 * sign-in. On Vercel `NODE_ENV` is `production`, so the NextAuth gate stays
 * fully active there.
 */
const isDevEnvironment = process.env.NODE_ENV !== "production";

export const proxy = isDevEnvironment
  ? () => NextResponse.next()
  : withAuth({
      pages: {
        signIn: "/login",
      },
    });

export const config = {
  matcher: [
    "/((?!login|api/auth|_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml|.*\\..*).*)",
  ],
};
