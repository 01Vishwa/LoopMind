"""auth.py — FastAPI JWT authentication dependency.

Extracts and verifies the Supabase-issued JWT from the
``Authorization: Bearer <token>`` request header, then injects the
authenticated user's ID and email into the route context via FastAPI's
dependency injection system.

All configuration is read from ``core.config`` — no credentials are
hard-coded here. The JWT secret is loaded from the ``SUPABASE_JWT_SECRET``
environment variable.

Usage in a route::

    from middleware.auth import get_current_user, AuthUser

    @router.post("/my-protected-route")
    async def my_route(auth: AuthUser = Depends(get_current_user)):
        return {"user_id": auth.user_id}

Optional / soft-auth usage (returns None when unauthenticated)::

    from middleware.auth import get_optional_user

    @router.get("/my-route")
    async def my_route(auth = Depends(get_optional_user)):
        user_id = auth.user_id if auth else None
"""

import logging
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from core.config import SUPABASE_JWT_SECRET

logger = logging.getLogger("uvicorn.error")

# ---------------------------------------------------------------------------
# HTTP Bearer extractor (FastAPI built-in)
# ---------------------------------------------------------------------------

_bearer_scheme = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# Domain model
# ---------------------------------------------------------------------------


class AuthUser(BaseModel):
    """Authenticated user identity extracted from the Supabase JWT.

    Attributes:
        user_id: UUID of the authenticated Supabase user (``sub`` claim).
        email:   User's email address from the JWT payload.
        role:    Supabase role claim (typically ``"authenticated"``).
    """

    user_id: str
    email: str
    role: str = "authenticated"


# ---------------------------------------------------------------------------
# Core verification logic
# ---------------------------------------------------------------------------


def _decode_supabase_jwt(token: str) -> dict:
    """Decodes and verifies a Supabase-issued JWT.

    Uses PyJWT with the HS256 algorithm and the ``SUPABASE_JWT_SECRET``
    configured in ``core.config``. The audience is not validated here
    because Supabase tokens use ``"authenticated"`` as the role claim
    rather than a standard audience value.

    Args:
        token: Raw JWT string (without the ``Bearer `` prefix).

    Returns:
        Decoded JWT payload dict.

    Raises:
        HTTPException 401: If the token is missing, expired, or invalid.
        HTTPException 500: If ``SUPABASE_JWT_SECRET`` is not configured.
    """
    if not SUPABASE_JWT_SECRET:
        logger.error(
            "[Auth] SUPABASE_JWT_SECRET is not set — cannot verify JWTs. "
            "Add it to backend/.env and restart the server."
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Auth service misconfigured: JWT secret missing.",
        )

    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as exc:
        logger.warning("[Auth] Invalid JWT: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _extract_auth_user(payload: dict) -> AuthUser:
    """Builds an AuthUser from a decoded JWT payload.

    Args:
        payload: Decoded Supabase JWT payload dict.

    Returns:
        AuthUser instance.

    Raises:
        HTTPException 401: If the ``sub`` claim is missing.
    """
    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing 'sub' claim.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email: str = payload.get("email", "")
    role: str = payload.get("role", "authenticated")

    return AuthUser(user_id=user_id, email=email, role=role)


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> AuthUser:
    """FastAPI dependency — requires a valid Supabase JWT.

    Injects an ``AuthUser`` into routes that mandate authentication.
    Returns HTTP 401 if the token is absent, expired, or invalid.

    Args:
        credentials: Extracted by FastAPI's HTTPBearer scheme.

    Returns:
        AuthUser: Authenticated user identity.

    Raises:
        HTTPException 401: On any auth failure.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = _decode_supabase_jwt(credentials.credentials)
    auth_user = _extract_auth_user(payload)
    logger.debug("[Auth] Authenticated user: %s", auth_user.user_id)
    return auth_user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Optional[AuthUser]:
    """FastAPI dependency — optional authentication.

    Returns an ``AuthUser`` when a valid token is present, otherwise
    returns ``None`` without raising an error. Use for endpoints that
    support both authenticated and anonymous access.

    Args:
        credentials: Extracted by FastAPI's HTTPBearer scheme (auto_error=False).

    Returns:
        AuthUser | None
    """
    if not credentials or not credentials.credentials:
        return None

    try:
        payload = _decode_supabase_jwt(credentials.credentials)
        return _extract_auth_user(payload)
    except HTTPException:
        return None
