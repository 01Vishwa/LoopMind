"""Retriever port — semantic search over file descriptions."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vera_core.models.file import FileDescription
from vera_core.models.ids import FileId, WorkspaceId


@runtime_checkable
class RetrieverPort(Protocol):
    """Find the most relevant file descriptions for a query.

    Used by the analyze node to provide context to the planner.
    """

    async def search(
        self,
        *,
        query: str,
        workspace_id: WorkspaceId,
        top_k: int = 12,
        pinned_file_ids: list[FileId] | None = None,
    ) -> list[FileDescription]: ...


__all__ = ["RetrieverPort"]
