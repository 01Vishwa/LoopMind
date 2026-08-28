"""VaultRepository — KeyVaultPort backed by Supabase Vault (supabase_vault)."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from vera_core.errors import NotFoundError
from vera_core.models.ids import TenantId

_DESCRIPTION = "VERA BYOK secret"


def _secret_name(tenant_id: TenantId, ref: str) -> str:
    return f"t:{tenant_id}:{ref}"


class VaultRepository:
    """Stores BYOK secrets in ``vault.secrets`` via Supabase Vault functions.

    Takes an :class:`AsyncSession` so the caller can commit the secret write in
    the same transaction as the provider-connection insert.
    """

    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def store(self, *, tenant_id: TenantId, ref: str, plaintext: str) -> None:
        name = _secret_name(tenant_id, ref)
        existing = (
            await self._session.execute(
                text("select id from vault.secrets where name = :name"), {"name": name}
            )
        ).scalar_one_or_none()
        if existing is not None:
            await self._session.execute(
                text("select vault.update_secret(:id, :secret)"),
                {"id": existing, "secret": plaintext},
            )
        else:
            await self._session.execute(
                text("select vault.create_secret(:secret, :name, :description)"),
                {"secret": plaintext, "name": name, "description": _DESCRIPTION},
            )

    async def retrieve(self, *, tenant_id: TenantId, ref: str) -> str:
        name = _secret_name(tenant_id, ref)
        result = (
            await self._session.execute(
                text("select decrypted_secret from vault.decrypted_secrets where name = :name"),
                {"name": name},
            )
        ).scalar_one_or_none()
        if result is None:
            raise NotFoundError(f"No vault secret for ref={ref!r} tenant={tenant_id}")
        return str(result)

    async def delete(self, *, tenant_id: TenantId, ref: str) -> None:
        name = _secret_name(tenant_id, ref)
        await self._session.execute(
            text("delete from vault.secrets where name = :name"), {"name": name}
        )


__all__ = ["VaultRepository"]
