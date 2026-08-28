from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from supabase._async.client import AsyncClient

from vera_api.dependencies.auth import Principal, get_current_user
from vera_api.dependencies.db import get_supabase_client
from vera_api.middleware.rate_limit import limiter, RATE_LIMITS
from vera_api.settings import settings
from supabase.client import ClientOptions
from supabase._async.client import create_client
from vera_api.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    SignupRequest,
    UserProfile,
    SignupResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest
)

router = APIRouter(prefix="/v1/auth", tags=["auth"])


def _build_auth_response(session, profile: dict) -> AuthResponse:
    """Convert a Supabase session + profile row into an AuthResponse."""
    return AuthResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        user=UserProfile(**profile)
    )


async def _load_profile(supabase: AsyncClient, user_id: str) -> dict:
    """Load public.profiles row for the given auth user id."""
    try:
        result = (
            await supabase.table("profiles")
            .select("*")
            .eq("id", user_id)
            .single()
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Could not load user profile") from exc

    if not result.data:
        raise HTTPException(status_code=404, detail="Profile not found")

    return result.data


@router.post("/signup", response_model=SignupResponse)
@limiter.limit(RATE_LIMITS["/v1/auth/signup"])
async def signup(
    request: Request,
    body: SignupRequest,
    supabase: AsyncClient = Depends(get_supabase_client),
) -> dict:
    """
    1. supabase.auth.sign_up({ email, password, options: { data: { full_name } } })
    2. DB trigger creates profile + tenant.
    3. Because email confirmation is ON, Supabase returns a user with no
       session (session=None) until they click the confirmation link.
    4. Return { status: "confirmation_sent", email } — NEVER return tokens
       here, since there's no active session yet.
    """
    try:
        result = await supabase.auth.sign_up(
            {
                "email": body.email,
                "password": body.password,
                "options": {"data": {"full_name": body.full_name}},
            }
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Signup failed.") from exc

    # Check for empty identities array to prevent email enumeration
    # When signing up an existing email, Supabase might return an empty identities array
    if result.user and hasattr(result.user, 'identities') and getattr(result.user, 'identities') == []:
        # Don't leak that the account already exists
        return {"status": "confirmation_sent", "email": body.email}

    return {"status": "confirmation_sent", "email": body.email}


async def inject_email(request: Request, body: LoginRequest):
    request.state.email = body.email

@router.post("/login", response_model=AuthResponse)
@limiter.limit(RATE_LIMITS["/v1/auth/login"])
async def login(
    request: Request,
    body: LoginRequest,
    supabase: AsyncClient = Depends(get_supabase_client),
    _=Depends(inject_email),
) -> AuthResponse:
    """
    1. supabase.auth.sign_in_with_password({ email, password })
    2. On any failure (wrong password, unconfirmed email, nonexistent email):
       return the SAME generic 401 {"detail": "invalid_credentials"}
       Exception: if "email not confirmed" is returned by Supabase, bubble that up.
    """
    try:
        result = await supabase.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except Exception as exc:
        error_msg = str(exc).lower()
        if "email not confirmed" in error_msg:
            raise HTTPException(status_code=401, detail="email_not_confirmed")
        raise HTTPException(status_code=401, detail="invalid_credentials")

    if not result.session or not result.user:
        raise HTTPException(status_code=401, detail="invalid_credentials")

    profile = await _load_profile(supabase, result.user.id)
    return _build_auth_response(result.session, profile)


@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    body: RefreshRequest,
    supabase: AsyncClient = Depends(get_supabase_client),
) -> AuthResponse:
    """Exchange a refresh token for a new access token."""
    try:
        result = await supabase.auth.refresh_session(body.refresh_token)
    except Exception as exc:
        # Hard logout if token reuse or invalid token
        raise HTTPException(status_code=401, detail="refresh_token_invalid")

    if not result.session or not result.user:
        raise HTTPException(status_code=401, detail="refresh_token_invalid")

    profile = await _load_profile(supabase, result.user.id)
    return _build_auth_response(result.session, profile)


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    principal: Principal = Depends(get_current_user),
    supabase: AsyncClient = Depends(get_supabase_client),
) -> None:
    """
    Calls supabase.auth.sign_out(scope="global") with the user's token.
    """
    auth_header = request.headers.get("Authorization")
    if auth_header:
        user_client = await create_client(
            settings.supabase_url,
            settings.supabase_anon_key.get_secret_value(),
            options=ClientOptions(headers={"Authorization": auth_header})
        )
        try:
            await user_client.auth.sign_out({"scope": "global"})
        except Exception:
            pass


@router.post("/forgot-password")
@limiter.limit(RATE_LIMITS["/v1/auth/forgot-password"])
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    supabase: AsyncClient = Depends(get_supabase_client),
):
    try:
        await supabase.auth.reset_password_for_email(
            body.email, 
            redirect_to="http://localhost:3000/auth/reset-password" # Make this driven by env var in prod
        )
    except Exception:
        # Ignore all errors to prevent enumeration
        pass
    
    return {"status": "if_exists_sent"}


@router.post("/reset-password")
@limiter.limit(RATE_LIMITS["/v1/auth/reset-password"])
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    principal: Principal = Depends(get_current_user),
    supabase: AsyncClient = Depends(get_supabase_client),
):
    """
    Using the recovery session, call supabase.auth.update_user({ password })
    """
    auth_header = request.headers.get("Authorization")
    if auth_header:
        user_client = await create_client(
            settings.supabase_url,
            settings.supabase_anon_key.get_secret_value(),
            options=ClientOptions(headers={"Authorization": auth_header})
        )
        try:
            await user_client.auth.update_user({"password": body.password})
            await user_client.auth.sign_out({"scope": "others"})
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Failed to reset password") from exc
    else:
        raise HTTPException(status_code=401, detail="missing_token")
        
    return {"status": "password_updated"}


@router.get("/me", response_model=UserProfile)
async def me(
    principal: Principal = Depends(get_current_user),
    supabase: AsyncClient = Depends(get_supabase_client),
) -> UserProfile:
    """Return the current user's profile. Called on every page load."""
    profile = await _load_profile(supabase, principal.user_id)
    return UserProfile(**profile)
