"""FastAPI application entry point.

Mounts the API router, registers middleware, and applies CORS. All
cross-cutting concerns (error handling) are imported from dedicated modules.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from api.routes import router as api_router
from middleware.error_handler import global_exception_handler


app = FastAPI(
    title="Agentloop Backend",
    description="Intelligent Document Processing API",
    version="1.0.0"
)

allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "*")
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",")] if allowed_origins_env else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(Exception, global_exception_handler)

app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
