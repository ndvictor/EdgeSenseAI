import { withAuth } from "next-auth/middleware";

/**
 * Auth gate for the entire app.
 *
 * Any request that is NOT explicitly excluded by the matcher below requires a
 * NextAuth session. Unauthenticated users are redirected to `/login` (with
 * `?callbackUrl=<original>` appended automatically by NextAuth) instead of
 * seeing a different provider's localized consent page or a 401.
 *
 * Public allowlist (handled by the matcher exclusions):
 *   - `/login`               (the sign-in page itself)
 *   - `/api/auth/*`          (NextAuth handlers — must stay open)
 *   - `/_next/static/*`,
 *     `/_next/image/*`       (build output)
 *   - `/favicon.ico`,
 *     `/robots.txt`,
 *     `/sitemap.xml`         (well-known files)
 *   - any path containing a `.` (static assets like .png, .svg, .css, .js)
 *
 * To make additional routes public (e.g. a marketing page), add them to the
 * negative-lookahead group below.
 */
export default withAuth({
  pages: {
    signIn: "/login",
  },
});

export const config = {
  matcher: [
    "/((?!login|api/auth|_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml|.*\\..*).*)",
  ],
};
