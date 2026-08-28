"""Key vault port — encrypted BYOK secret storage."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vera_core.models.ids import TenantId


@runtime_checkable
class KeyVaultPort(Protocol):
    """Store and retrieve encrypted secrets per tenant.

    The ref is a logical key (e.g. "provider:<conn_id>:api_key").
    Implementations encrypt before storage and decrypt on retrieval.
    The plaintext is never logged or returned to the API layer.
    """

    async def store(self, *, tenant_id: TenantId, ref: str, plaintext: str) -> None: ...

    async def retrieve(self, *, tenant_id: TenantId, ref: str) -> str: ...

    async def delete(self, *, tenant_id: TenantId, ref: str) -> None: ...


__all__ = ["KeyVaultPort"]
