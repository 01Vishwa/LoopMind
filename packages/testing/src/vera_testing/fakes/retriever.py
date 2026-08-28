"""FakeRetriever — scripted retriever implementation for unit tests."""

from __future__ import annotations

from vera_core.models.file import FileDescription
from vera_core.models.ids import FileId, WorkspaceId


class FakeRetriever:
    """Returns a fixed list of file descriptions, truncated to ``top_k``."""

    def __init__(self, descriptions: list[FileDescription] | None = None) -> None:
        self._descriptions: list[FileDescription] = list(descriptions or [])

    def set_results(self, descriptions: list[FileDescription]) -> None:
        self._descriptions = list(descriptions)

    async def search(
        self,
        *,
        query: str,
        workspace_id: WorkspaceId,
        top_k: int = 12,
        pinned_file_ids: list[FileId] | None = None,
    ) -> list[FileDescription]:
        return list(self._descriptions)[:top_k]


__all__ = ["FakeRetriever"]
