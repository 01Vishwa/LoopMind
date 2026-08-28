import os
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# If AUTH_RATE_LIMIT_REDIS_URL is not provided, it falls back to in-memory limit.
# In production, make sure to set AUTH_RATE_LIMIT_REDIS_URL in the .env file.
redis_url = os.environ.get("AUTH_RATE_LIMIT_REDIS_URL")

def get_email_and_ip(request: Request) -> str:
    ip = get_remote_address(request)
    email = getattr(request.state, "email", "")
    if email:
        return f"{ip}:{email}"
    return ip

if redis_url:
    limiter = Limiter(key_func=get_email_and_ip, storage_uri=redis_url)
else:
    limiter = Limiter(key_func=get_email_and_ip)

def _rate_limit_handler(request: Request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many attempts. Try again later."},
    )

def setup_rate_limiting(app: FastAPI):
    app.state.limiter = limiter
    app.add_exception_handler(429, _rate_limit_handler)

RATE_LIMITS = {
    "/v1/auth/signup":          "5/hour",
    "/v1/auth/login":           "10/15minute",
    "/v1/auth/forgot-password": "3/hour",
    "/v1/auth/reset-password":  "5/hour",
}


