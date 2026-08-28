"""WorkspaceRepository — SQLAlchemy implementation."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from vera_db.models.workspace import Workspace
from vera_db.models.file import FileRecord
from vera_db.models.description import FileDescription


class WorkspaceRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, *, id: uuid.UUID, tenant_id: uuid.UUID, created_by: uuid.UUID, name: str, description: str | None
    ) -> Workspace:
        row = Workspace(
            id=id,
            tenant_id=tenant_id,
            created_by=created_by,
            name=name,
            description=description,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get(self, *, workspace_id: uuid.UUID, tenant_id: uuid.UUID) -> Workspace | None:
        stmt = select(Workspace).where(Workspace.id == workspace_id, Workspace.tenant_id == tenant_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_for_tenant(self, *, tenant_id: uuid.UUID, cursor: Any = None, limit: int = 50) -> list[Workspace]:
        stmt = (
            select(Workspace)
            .where(Workspace.tenant_id == tenant_id)
            .order_by(Workspace.created_at.desc())
            .limit(limit)
        )
        # Note: cursor pagination can be implemented later, simple limit for now
        return list((await self._session.execute(stmt)).scalars().all())

    async def update(self, *, workspace_id: uuid.UUID, tenant_id: uuid.UUID, name: str | None = None, description: str | None = None) -> Workspace | None:
        stmt = select(Workspace).where(Workspace.id == workspace_id, Workspace.tenant_id == tenant_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if not row:
            return None
        
        if name is not None:
            row.name = name
        if description is not None:
            row.description = description
            
        row.updated_at = func.now()
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def delete(self, *, workspace_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        await self._session.execute(
            delete(Workspace).where(Workspace.id == workspace_id, Workspace.tenant_id == tenant_id)
        )
        await self._session.flush()

    async def get_with_counts(self, *, workspace_id: uuid.UUID, tenant_id: uuid.UUID) -> dict[str, Any] | None:
        # A simple query to get the workspace + file_count + described_count
        stmt = (
            select(
                Workspace,
                func.count(FileRecord.id).label("file_count"),
                func.count(FileDescription.id).label("described_count")
            )
            .outerjoin(FileRecord, FileRecord.workspace_id == Workspace.id)
            .outerjoin(FileDescription, FileDescription.file_id == FileRecord.id)
            .where(Workspace.id == workspace_id, Workspace.tenant_id == tenant_id)
            .group_by(Workspace.id)
        )
        result = (await self._session.execute(stmt)).first()
        if not result:
            return None
        
        workspace, file_count, described_count = result
        return {
            "workspace": workspace,
            "file_count": file_count,
            "described_count": described_count
        }

__all__ = ["WorkspaceRepository"]
