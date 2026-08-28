"""
FastAPI application entry point for vera-api.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vera_api.routers import health
from vera_api.routers.v1 import auth as auth_router
from vera_api.routers.v1 import providers as providers_router
from vera_api.routers.v1 import settings as settings_router
from vera_api.settings import settings
from vera_api.middleware.rate_limit import setup_rate_limiting

app = FastAPI(
    title="VERA API",
    description="Backend for VERA — Verifiable Data Analysis",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

from vera_api.routers.v1 import files as files_router
from vera_api.routers.v1 import ingest as ingest_router
from vera_api.routers.v1 import descriptions as descriptions_router
from vera_api.routers.v1 import workspaces as workspaces_router

app.include_router(health.router)
app.include_router(auth_router.router)
app.include_router(providers_router.router, prefix="/v1")
app.include_router(settings_router.router, prefix="/v1")
app.include_router(workspaces_router.router, prefix="/v1")
app.include_router(files_router.router, prefix="/v1")
app.include_router(ingest_router.router, prefix="/v1")
app.include_router(descriptions_router.router, prefix="/v1")

setup_rate_limiting(app)
