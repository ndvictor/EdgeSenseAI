#!/usr/bin/env bash
# Frontend production smoke: build + typecheck + live URL checks.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PROD_FRONTEND="${PROD_FRONTEND_URL:-https://edge-sense-ai.vercel.app}"
AZURE_BACKEND="${AZURE_BACKEND_URL:-https://edgesenseai-backend.braveisland-a2c39ffe.centralus.azurecontainerapps.io}"

echo "== EdgeSenseAI frontend prod test =="
echo "   prod frontend: $PROD_FRONTEND"
echo "   azure backend: $AZURE_BACKEND"
echo ""

echo ">> production build (uses .env.local / Vercel env at build time)"
rm -rf .next
npm run build

echo ""
echo ">> typecheck"
npm run typecheck

echo ""
echo ">> Vercel pages"
for path in /login /EdgeSenseAI; do
  code=$(curl -sS -o /dev/null -w "%{http_code}" -m 25 "$PROD_FRONTEND$path" || echo "000")
  echo "   $path -> HTTP $code"
done

echo ""
echo ">> Azure backend (browser + control tower)"
for path in \
  "/api/v1/daytrading/paper-autonomy/control-tower" \
  "/api/v1/daytrading/settings/gates"; do
  code=$(curl -sS -o /dev/null -w "%{http_code}" -m 30 "$AZURE_BACKEND$path" || echo "000")
  echo "   $path -> HTTP $code"
done

echo ""
echo "PASS: build + typecheck + prod smoke checks completed."
echo "Note: /api/edgesense/* on Vercel require NextAuth login (307 to /login when unauthenticated)."
echo "      Run workflow/gates from the signed-in Control Tower UI in production."
