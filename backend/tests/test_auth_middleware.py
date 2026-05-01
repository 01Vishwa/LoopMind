"""test_auth_middleware.py — Unit tests for the FastAPI JWT auth dependency.

Tests cover:
- Valid JWT is decoded and returns AuthUser with correct fields.
- Missing Authorization header raises HTTP 401.
- Expired JWT raises HTTP 401.
- Tampered / invalid JWT raises HTTP 401.
- Missing SUPABASE_JWT_SECRET raises HTTP 500.
- get_optional_user returns None (no raise) for missing / invalid tokens.

All tests run without a real Supabase connection — JWTs are generated
in-process using PyJWT with a synthetic secret.
"""

import time
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from middleware import auth

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEST_SECRET = "test-super-secret"
_TEST_USER_ID = "00000000-0000-0000-0000-000000000001"
_TEST_EMAIL = "test@example.com"


def _make_token(
    user_id: str = _TEST_USER_ID,
    email: str = _TEST_EMAIL,
    role: str = "authenticated",
    secret: str = _TEST_SECRET,
    exp_offset: int = 3600,
) -> str:
    """Generates a synthetic Supabase-style HS256 JWT for testing.

    Args:
        user_id:    Subject claim (UUID string).
        email:      User email claim.
        role:       Supabase role claim.
        secret:     HMAC secret to sign the token.
        exp_offset: Seconds from now for expiry (negative = already expired).

    Returns:
        Encoded JWT string.
    """
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "iss": "supabase",
        "aud": "authenticated",
        "iat": int(time.time()),
        "exp": int(time.time()) + exp_offset,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def _make_credentials(token: str) -> HTTPAuthorizationCredentials:
    """Wraps a raw token string in an HTTPAuthorizationCredentials object."""
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def patch_jwt_secret():
    """Replaces SUPABASE_JWT_SECRET with the test secret for every test."""
    with patch.object(auth, "SUPABASE_JWT_SECRET", _TEST_SECRET):
        yield


# ---------------------------------------------------------------------------
# Tests: _decode_supabase_jwt
# ---------------------------------------------------------------------------


class TestDecodeSupabaseJwt:
    """Tests for the internal _decode_supabase_jwt helper."""

    def test_valid_token_returns_payload(self):
        """A well-formed, unexpired token should decode to the expected claims."""
        from middleware.auth import _decode_supabase_jwt

        token = _make_token()
        payload = _decode_supabase_jwt(token)

        assert payload["sub"] == _TEST_USER_ID
        assert payload["email"] == _TEST_EMAIL
        assert payload["role"] == "authenticated"

    def test_expired_token_raises_401(self):
        """An expired token must raise HTTP 401."""
        from middleware.auth import _decode_supabase_jwt

        expired_token = _make_token(exp_offset=-1)

        with pytest.raises(HTTPException) as exc_info:
            _decode_supabase_jwt(expired_token)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    def test_tampered_token_raises_401(self):
        """A token signed with the wrong key should raise HTTP 401."""
        from middleware.auth import _decode_supabase_jwt

        tampered = _make_token(secret="wrong-secret")

        with pytest.raises(HTTPException) as exc_info:
            _decode_supabase_jwt(tampered)

        assert exc_info.value.status_code == 401

    def test_garbage_string_raises_401(self):
        """A completely invalid token string should raise HTTP 401."""
        from middleware.auth import _decode_supabase_jwt

        with pytest.raises(HTTPException) as exc_info:
            _decode_supabase_jwt("not.a.jwt")

        assert exc_info.value.status_code == 401

    def test_missing_jwt_secret_raises_500(self):
        """When SUPABASE_JWT_SECRET is empty, HTTP 500 is raised."""
        from middleware.auth import _decode_supabase_jwt

        token = _make_token()
        with patch.object(auth, "SUPABASE_JWT_SECRET", ""):
            with pytest.raises(HTTPException) as exc_info:
                _decode_supabase_jwt(token)

        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# Tests: _extract_auth_user
# ---------------------------------------------------------------------------


class TestExtractAuthUser:
    """Tests for _extract_auth_user (builds AuthUser from decoded payload)."""

    def test_full_payload_maps_correctly(self):
        """All standard claims are mapped to AuthUser fields."""
        from middleware.auth import _extract_auth_user

        payload = {
            "sub": _TEST_USER_ID,
            "email": _TEST_EMAIL,
            "role": "authenticated",
        }
        user = _extract_auth_user(payload)

        assert user.user_id == _TEST_USER_ID
        assert user.email == _TEST_EMAIL
        assert user.role == "authenticated"

    def test_missing_sub_raises_401(self):
        """A payload without 'sub' must raise HTTP 401."""
        from middleware.auth import _extract_auth_user

        with pytest.raises(HTTPException) as exc_info:
            _extract_auth_user({"email": _TEST_EMAIL})

        assert exc_info.value.status_code == 401

    def test_missing_email_defaults_to_empty_string(self):
        """A payload without 'email' should still produce a valid AuthUser."""
        from middleware.auth import _extract_auth_user

        user = _extract_auth_user({"sub": _TEST_USER_ID})
        assert user.email == ""
        assert user.user_id == _TEST_USER_ID

    def test_role_defaults_to_authenticated(self):
        """Missing 'role' claim should default to 'authenticated'."""
        from middleware.auth import _extract_auth_user

        user = _extract_auth_user({"sub": _TEST_USER_ID, "email": _TEST_EMAIL})
        assert user.role == "authenticated"


# ---------------------------------------------------------------------------
# Tests: get_current_user (async dependency)
# ---------------------------------------------------------------------------


class TestGetCurrentUser:
    """Async tests for the get_current_user FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_valid_credentials_returns_auth_user(self):
        """Valid credentials produce an AuthUser with correct user_id."""
        from middleware.auth import get_current_user

        token = _make_token()
        creds = _make_credentials(token)

        result = await get_current_user(credentials=creds)

        assert result.user_id == _TEST_USER_ID
        assert result.email == _TEST_EMAIL

    @pytest.mark.asyncio
    async def test_missing_credentials_raises_401(self):
        """No credentials at all must raise HTTP 401."""
        from middleware.auth import get_current_user

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=None)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_token_raises_401(self):
        """Credentials object with empty string token must raise HTTP 401."""
        from middleware.auth import get_current_user

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="")
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=creds)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_token_raises_401(self):
        """An expired token passed to get_current_user must raise HTTP 401."""
        from middleware.auth import get_current_user

        token = _make_token(exp_offset=-10)
        creds = _make_credentials(token)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=creds)

        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# Tests: get_optional_user (async soft-auth dependency)
# ---------------------------------------------------------------------------


class TestGetOptionalUser:
    """Async tests for get_optional_user — returns None instead of raising."""

    @pytest.mark.asyncio
    async def test_valid_token_returns_auth_user(self):
        """A valid token should return an AuthUser (same as get_current_user)."""
        from middleware.auth import get_optional_user

        token = _make_token()
        creds = _make_credentials(token)

        result = await get_optional_user(credentials=creds)

        assert result is not None
        assert result.user_id == _TEST_USER_ID

    @pytest.mark.asyncio
    async def test_missing_credentials_returns_none(self):
        """No credentials → None (not a 401 exception)."""
        from middleware.auth import get_optional_user

        result = await get_optional_user(credentials=None)
        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_token_returns_none(self):
        """A bad token should silently return None for optional auth."""
        from middleware.auth import get_optional_user

        creds = _make_credentials("invalid.jwt.token")
        result = await get_optional_user(credentials=creds)
        assert result is None

    @pytest.mark.asyncio
    async def test_expired_token_returns_none(self):
        """An expired token with optional auth should return None, not raise."""
        from middleware.auth import get_optional_user

        token = _make_token(exp_offset=-10)
        creds = _make_credentials(token)

        result = await get_optional_user(credentials=creds)
        assert result is None


# ---------------------------------------------------------------------------
# Tests: AuthUser model
# ---------------------------------------------------------------------------


class TestAuthUserModel:
    """Tests for the AuthUser Pydantic model itself."""

    def test_default_role(self):
        """AuthUser role defaults to 'authenticated'."""
        from middleware.auth import AuthUser

        user = AuthUser(user_id=_TEST_USER_ID, email=_TEST_EMAIL)
        assert user.role == "authenticated"

    def test_fields_are_immutable_strings(self):
        """user_id and email must be strings."""
        from middleware.auth import AuthUser

        user = AuthUser(user_id=_TEST_USER_ID, email=_TEST_EMAIL, role="service_role")
        assert isinstance(user.user_id, str)
        assert isinstance(user.email, str)
        assert user.role == "service_role"
