"""FakeKeyVault — in-memory key vault for tests."""

from __future__ import annotations

from vera_core.errors import NotFoundError
from vera_core.models.ids import TenantId


class FakeKeyVault:
    """In-memory vault. Keys are namespaced by (tenant_id, ref).

    Does not encrypt — purely for test isolation.
    """

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], str] = {}
        self.store_calls: int = 0
        self.retrieve_calls: int = 0
        self.delete_calls: int = 0

    async def store(self, *, tenant_id: TenantId, ref: str, plaintext: str) -> None:
        self.store_calls += 1
        self._store[(str(tenant_id), ref)] = plaintext

    async def retrieve(self, *, tenant_id: TenantId, ref: str) -> str:
        self.retrieve_calls += 1
        key = (str(tenant_id), ref)
        if key not in self._store:
            raise NotFoundError(f"Key not found: ref={ref!r} tenant={tenant_id}")
        return self._store[key]

    async def delete(self, *, tenant_id: TenantId, ref: str) -> None:
        self.delete_calls += 1
        self._store.pop((str(tenant_id), ref), None)

    def entries(self) -> dict[tuple[str, str], str]:
        """Return a copy of all stored entries (for assertions)."""
        return dict(self._store)

    def __len__(self) -> int:
        return len(self._store)


__all__ = ["FakeKeyVault"]
