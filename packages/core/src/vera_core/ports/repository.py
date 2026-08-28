"""Repository ports — data access interfaces for domain objects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from vera_core.models.agent_config import AgentDefaults
from vera_core.models.file import FileDescription, FileRef
from vera_core.models.ids import (
    FileId,
    ProviderConnectionId,
    RunId,
    TenantId,
    UserId,
    WorkspaceId,
)
from vera_core.models.provider import ProviderConnection
from vera_core.models.run import RunState


@dataclass(frozen=True)
class Page[T]:
    """Cursor-paginated result page."""

    items: list[T]
    next_cursor: str | None  # None means no more pages


class RunSummary:
    """Lightweight run record for list views."""

    run_id: RunId
    query: str
    status: str
    mode: str
    cost_usd: str
    total_tokens: int
    started_at: str
    finished_at: str | None


@runtime_checkable
class RunRepositoryPort(Protocol):
    async def create(self, *, run: RunState) -> RunState: ...
    async def get(self, *, run_id: RunId, tenant_id: TenantId) -> RunState | None: ...
    async def update(self, *, run: RunState) -> RunState: ...
    async def list_for_user(
        self, *, user_id: UserId, cursor: str | None, limit: int
    ) -> Page[RunState]: ...


@runtime_checkable
class ProviderRepositoryPort(Protocol):
    async def create_connection(self, *, conn: ProviderConnection) -> ProviderConnection: ...
    async def get_connection(
        self, *, id: ProviderConnectionId, tenant_id: TenantId
    ) -> ProviderConnection | None: ...
    async def list_connections(self, *, user_id: UserId) -> list[ProviderConnection]: ...
    async def update_connection(self, *, conn: ProviderConnection) -> ProviderConnection: ...
    async def delete_connection(self, *, id: ProviderConnectionId, tenant_id: TenantId) -> None: ...


@runtime_checkable
class AgentDefaultsRepositoryPort(Protocol):
    async def get(self, *, user_id: UserId) -> AgentDefaults | None: ...
    async def upsert(self, *, defaults: AgentDefaults) -> AgentDefaults: ...


@runtime_checkable
class WorkspaceRepositoryPort(Protocol):
    async def create(self, *, name: str, user_id: UserId, tenant_id: TenantId) -> object: ...
    async def get(self, *, workspace_id: WorkspaceId, tenant_id: TenantId) -> object | None: ...
    async def list_for_user(self, *, user_id: UserId) -> list[object]: ...
    async def delete(self, *, workspace_id: WorkspaceId, tenant_id: TenantId) -> None: ...


@runtime_checkable
class FileRepositoryPort(Protocol):
    async def create(self, *, file_ref: FileRef) -> FileRef: ...
    async def get(self, *, file_id: FileId, tenant_id: TenantId) -> FileRef | None: ...
    async def list_for_workspace(self, *, workspace_id: WorkspaceId) -> list[FileRef]: ...
    async def get_description(self, *, file_id: FileId) -> FileDescription | None: ...
    async def save_description(self, *, desc: FileDescription) -> FileDescription: ...
    async def delete(self, *, file_id: FileId, tenant_id: TenantId) -> None: ...


__all__ = [
    "Page",
    "RunSummary",
    "RunRepositoryPort",
    "ProviderRepositoryPort",
    "AgentDefaultsRepositoryPort",
    "WorkspaceRepositoryPort",
    "FileRepositoryPort",
]
