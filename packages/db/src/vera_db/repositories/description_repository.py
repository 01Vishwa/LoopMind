"""DescriptionRepository — SQLAlchemy implementation."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from vera_db.models.description import FileDescription


class DescriptionRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        file_id: uuid.UUID,
        tenant_id: uuid.UUID,
        summary_text: str,
        schema_fields: list[dict[str, Any]] | None = None,
        row_count: int | None = None,
        sheet_names: list[str] | None = None,
        sample_rows: list[dict[str, Any]] | None = None,
        analyzer_script: str | None = None,
        analyzer_model: str,
        prompt_version: str,
        embedding: Any = None,
    ) -> FileDescription:
        row = FileDescription(
            file_id=file_id,
            tenant_id=tenant_id,
            summary_text=summary_text,
            schema_fields=schema_fields,
            row_count=row_count,
            sheet_names=sheet_names,
            sample_rows=sample_rows,
            analyzer_script=analyzer_script,
            analyzer_model=analyzer_model,
            prompt_version=prompt_version,
            embedding=embedding,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get_by_file(self, *, file_id: uuid.UUID, tenant_id: uuid.UUID) -> FileDescription | None:
        stmt = select(FileDescription).where(
            FileDescription.file_id == file_id, FileDescription.tenant_id == tenant_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def delete_by_file(self, *, file_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        await self._session.execute(
            delete(FileDescription).where(
                FileDescription.file_id == file_id, FileDescription.tenant_id == tenant_id
            )
        )
        await self._session.flush()

    async def list_by_workspace(self, *, workspace_id: uuid.UUID, tenant_id: uuid.UUID) -> list[FileDescription]:
        from vera_db.models.file import FileRecord
        stmt = (
            select(FileDescription)
            .join(FileRecord, FileRecord.id == FileDescription.file_id)
            .where(
                FileRecord.workspace_id == workspace_id,
                FileDescription.tenant_id == tenant_id
            )
        )
        return list((await self._session.execute(stmt)).scalars().all())


__all__ = ["DescriptionRepository"]
