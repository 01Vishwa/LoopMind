"""VERA error taxonomy.

All errors inherit from VeraError. The API layer maps these to RFC 9457
application/problem+json responses using the status and type_uri attributes.
"""

from __future__ import annotations


class VeraError(Exception):
    """Base class for all VERA application errors."""

    status: int = 500
    type_uri: str = "urn:vera:error:internal"

    def __init__(self, detail: str = "An unexpected error occurred") -> None:
        super().__init__(detail)
        self.detail = detail

    def __str__(self) -> str:
        return self.detail


# ── HTTP / access errors ──────────────────────────────────────────────────────


class NotFoundError(VeraError):
    status = 404
    type_uri = "urn:vera:error:not-found"

    def __init__(self, detail: str = "Resource not found") -> None:
        super().__init__(detail)


class ForbiddenError(VeraError):
    status = 403
    type_uri = "urn:vera:error:forbidden"

    def __init__(self, detail: str = "Access denied") -> None:
        super().__init__(detail)


class UnauthorizedError(VeraError):
    status = 401
    type_uri = "urn:vera:error:unauthorized"

    def __init__(self, detail: str = "Authentication required") -> None:
        super().__init__(detail)


class ValidationError(VeraError):
    status = 422
    type_uri = "urn:vera:error:validation"

    def __init__(self, detail: str = "Validation failed") -> None:
        super().__init__(detail)


class ConflictError(VeraError):
    status = 409
    type_uri = "urn:vera:error:conflict"

    def __init__(self, detail: str = "Resource conflict") -> None:
        super().__init__(detail)


# ── Provider / BYOK errors ────────────────────────────────────────────────────


class NeedsProviderError(VeraError):
    status = 422
    type_uri = "urn:vera:error:needs-provider"

    def __init__(self, detail: str = "Connect a model provider before starting a run") -> None:
        super().__init__(detail)


class NeedsConfigError(VeraError):
    status = 422
    type_uri = "urn:vera:error:needs-config"

    def __init__(self, detail: str = "Configure model assignments in Agent Defaults") -> None:
        super().__init__(detail)


class ProviderAuthError(VeraError):
    status = 502
    type_uri = "urn:vera:error:provider-auth"

    def __init__(self, detail: str = "Provider authentication failed") -> None:
        super().__init__(detail)


class ProviderUnavailableError(VeraError):
    status = 503
    type_uri = "urn:vera:error:provider-unavailable"

    def __init__(self, detail: str = "Provider temporarily unavailable") -> None:
        super().__init__(detail)


class ProviderRateLimitError(VeraError):
    status = 429
    type_uri = "urn:vera:error:provider-rate-limit"

    def __init__(self, detail: str = "Provider rate limit exceeded") -> None:
        super().__init__(detail)


class ProviderResponseError(VeraError):
    status = 502
    type_uri = "urn:vera:error:provider-response"

    def __init__(self, detail: str = "Invalid response from provider") -> None:
        super().__init__(detail)


# ── Run errors ────────────────────────────────────────────────────────────────


class BudgetExhaustedError(VeraError):
    """Returned as HTTP 200 — the run completed but hit its budget ceiling."""

    status = 200
    type_uri = "urn:vera:error:budget-exhausted"

    def __init__(self, detail: str = "Run budget exhausted") -> None:
        super().__init__(detail)


class SandboxTimeoutError(VeraError):
    status = 500
    type_uri = "urn:vera:error:sandbox-timeout"

    def __init__(self, detail: str = "Sandbox execution timed out") -> None:
        super().__init__(detail)


class AgentOutputError(VeraError):
    status = 500
    type_uri = "urn:vera:error:agent-output"

    def __init__(self, detail: str = "Agent produced invalid output") -> None:
        super().__init__(detail)


class RunCancelledError(VeraError):
    status = 200
    type_uri = "urn:vera:error:run-cancelled"

    def __init__(self, detail: str = "Run was cancelled") -> None:
        super().__init__(detail)


# ── Storage errors ────────────────────────────────────────────────────────────


class ObjectNotFoundError(VeraError):
    status = 404
    type_uri = "urn:vera:error:object-not-found"

    def __init__(self, detail: str = "Object not found in store") -> None:
        super().__init__(detail)


class ImportDeniedError(VeraError):
    """Raised by the AST scanner when a blocked import is found in generated code."""

    status = 400
    type_uri = "urn:vera:error:import-denied"

    def __init__(self, detail: str = "Script imports a blocked module") -> None:
        super().__init__(detail)


class SandboxNotAvailableError(VeraError):
    """Raised when subprocess sandbox is requested but VERA_SANDBOX_ALLOW_SUBPROCESS is not set."""

    status = 503
    type_uri = "urn:vera:error:sandbox-not-available"

    def __init__(
        self, detail: str = "Sandbox backend is not available in this environment"
    ) -> None:
        super().__init__(detail)


__all__ = [
    "VeraError",
    "NotFoundError",
    "ForbiddenError",
    "UnauthorizedError",
    "ValidationError",
    "ConflictError",
    "NeedsProviderError",
    "NeedsConfigError",
    "ProviderAuthError",
    "ProviderUnavailableError",
    "ProviderRateLimitError",
    "ProviderResponseError",
    "BudgetExhaustedError",
    "SandboxTimeoutError",
    "AgentOutputError",
    "RunCancelledError",
    "ObjectNotFoundError",
    "ImportDeniedError",
    "SandboxNotAvailableError",
]
