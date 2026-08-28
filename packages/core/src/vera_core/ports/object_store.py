"""Object store port — binary blob storage."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class PresignedUpload(BaseModel):
    upload_url: str  # PUT to this URL
    public_url: str  # GET from this URL after upload
    expires_in_s: int = 3600

    model_config = {"frozen": True}


@runtime_checkable
class ObjectStorePort(Protocol):
    """Store and retrieve raw bytes. Key is an opaque string (e.g. SHA-256 hash)."""

    async def put(
        self, *, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str: ...

    async def get(self, *, key: str) -> bytes: ...

    async def delete(self, *, key: str) -> None: ...

    async def presign_upload(
        self,
        *,
        key: str,
        content_type: str,
        max_bytes: int,
    ) -> PresignedUpload: ...


__all__ = ["PresignedUpload", "ObjectStorePort"]
