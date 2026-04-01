"""Global exception middleware.

Moved from main.py to keep the application entry point lean.
Traps any unhandled exception and serializes it into a structured
JSON Toast-compatible error payload for the frontend.
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from models.schemas import ErrorResponse


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Traps generic exceptions to yield structured JSON.

    Ensures raw tracebacks are never exposed to the frontend, instead
    formatting them to trigger 'error' toasts in the UI.

    Args:
        request (Request): The incoming FastAPI request object.
        exc (Exception): The unhandled exception that was raised.

    Returns:
        JSONResponse: A 500 response with a structured ErrorResponse body.
    """
    error_content = ErrorResponse(
        status="error",
        message=f"An unexpected error occurred: {str(exc)}"
    )
    return JSONResponse(
        status_code=500,
        content=error_content.model_dump()
    )
