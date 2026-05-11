"""FastAPI dependency that gates mutation/run endpoints behind an admin token.

The token is read from the ``OPS_ADMIN_TOKEN`` environment variable on the
backend (Azure Container App / local). Callers must send it in the
``X-Ops-Admin-Token`` HTTP header.

Why a header token (and not just CORS / NextAuth):

- CORS only restricts *browser* origins. Server-to-server callers (or
  ``curl``) can hit Azure freely otherwise.
- NextAuth lives on the *frontend*. The Azure backend never sees the
  Google session; it only sees the proxied request.
- The Vercel Next.js route enforces NextAuth, then forwards to Azure with
  the secret header. That gives us "signed-in owner + secret token" without
  putting the secret in the browser.

If ``OPS_ADMIN_TOKEN`` is unset on the backend, all calls to these
endpoints are rejected with HTTP 503. This is deliberate: an unset token
means the operator has not opted in to remote mutations.
"""

from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException, status


_ADMIN_TOKEN_HEADER = "X-Ops-Admin-Token"


def _expected_token() -> str | None:
    raw = os.environ.get("OPS_ADMIN_TOKEN")
    if raw is None:
        return None
    cleaned = raw.strip()
    return cleaned or None


def require_ops_admin_token(
    x_ops_admin_token: str | None = Header(default=None, alias=_ADMIN_TOKEN_HEADER),
) -> str:
    """FastAPI dependency that enforces the ops admin token.

    Returns the validated token (callers do not usually need it). Raises
    :class:`fastapi.HTTPException` with 503 when the backend is not
    configured with a token, 401 when the header is missing, and 403 when
    the token does not match.
    """
    expected = _expected_token()
    if expected is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ops_admin_token_not_configured",
        )
    if not x_ops_admin_token or not x_ops_admin_token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing_ops_admin_token",
        )
    if not hmac.compare_digest(x_ops_admin_token.strip(), expected):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="invalid_ops_admin_token",
        )
    return expected


def ops_admin_token_configured() -> bool:
    """Whether the backend has an ``OPS_ADMIN_TOKEN`` configured.

    Exposed so read-only endpoints can advertise whether mutation is even
    possible from this deployment.
    """
    return _expected_token() is not None


__all__ = [
    "ops_admin_token_configured",
    "require_ops_admin_token",
]
