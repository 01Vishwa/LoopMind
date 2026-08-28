"""FileRepository — SQLAlchemy implementation."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from vera_db.models.file import FileRecord
from vera_db.models.description import FileDescription


class FileRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        id: uuid.UUID,
        workspace_id: uuid.UUID,
        tenant_id: uuid.UUID,
        filename: str,
        kind: str,
        size_bytes: int,
        content_sha256: str,
        storage_path: str,
        uploaded_by: uuid.UUID,
    ) -> FileRecord:
        row = FileRecord(
            id=id,
            workspace_id=workspace_id,
            tenant_id=tenant_id,
            filename=filename,
            kind=kind,
            size_bytes=size_bytes,
            content_sha256=content_sha256,
            storage_path=storage_path,
            uploaded_by=uploaded_by,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get(self, *, file_id: uuid.UUID, tenant_id: uuid.UUID) -> FileRecord | None:
        stmt = select(FileRecord).where(FileRecord.id == file_id, FileRecord.tenant_id == tenant_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_by_workspace(self, *, workspace_id: uuid.UUID, tenant_id: uuid.UUID) -> list[FileRecord]:
        stmt = select(FileRecord).where(
            FileRecord.workspace_id == workspace_id, FileRecord.tenant_id == tenant_id
        ).order_by(FileRecord.created_at.desc())
        return list((await self._session.execute(stmt)).scalars().all())

    async def find_by_sha(self, *, workspace_id: uuid.UUID, content_sha256: str) -> FileRecord | None:
        stmt = select(FileRecord).where(
            FileRecord.workspace_id == workspace_id, FileRecord.content_sha256 == content_sha256
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_without_description(self, *, workspace_id: uuid.UUID, tenant_id: uuid.UUID) -> list[FileRecord]:
        # Using a left outer join and filtering for null description id
        stmt = (
            select(FileRecord)
            .outerjoin(FileDescription, FileDescription.file_id == FileRecord.id)
            .where(
                FileRecord.workspace_id == workspace_id,
                FileRecord.tenant_id == tenant_id,
                FileDescription.id.is_(None)
            )
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def delete(self, *, file_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        await self._session.execute(
            delete(FileRecord).where(FileRecord.id == file_id, FileRecord.tenant_id == tenant_id)
        )
        await self._session.flush()

__all__ = ["FileRepository"]
