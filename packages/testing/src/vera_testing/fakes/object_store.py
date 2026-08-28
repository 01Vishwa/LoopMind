"""MemoryObjectStore — in-memory object store for tests."""

from __future__ import annotations

from vera_core.errors import ObjectNotFoundError
from vera_core.ports.object_store import PresignedUpload


class MemoryObjectStore:
    """Stores objects in-memory. PresignedUpload returns fake URLs."""

    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}
        self._content_types: dict[str, str] = {}

    async def put(
        self, *, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        self._store[key] = data
        self._content_types[key] = content_type
        return key

    async def get(self, *, key: str) -> bytes:
        if key not in self._store:
            raise ObjectNotFoundError(f"Object not found: {key!r}")
        return self._store[key]

    async def delete(self, *, key: str) -> None:
        self._store.pop(key, None)
        self._content_types.pop(key, None)

    async def presign_upload(
        self,
        *,
        key: str,
        content_type: str,
        max_bytes: int,
    ) -> PresignedUpload:
        return PresignedUpload(
            upload_url=f"http://fake-store/upload/{key}",
            public_url=f"http://fake-store/{key}",
            expires_in_s=3600,
        )

    def __contains__(self, key: str) -> bool:
        return key in self._store

    def __len__(self) -> int:
        return len(self._store)


__all__ = ["MemoryObjectStore"]
