"""VERA domain ID types — thin NewType wrappers around UUID for compile-time safety."""

from typing import NewType
from uuid import UUID

TenantId = NewType("TenantId", UUID)
UserId = NewType("UserId", UUID)
WorkspaceId = NewType("WorkspaceId", UUID)
FileId = NewType("FileId", UUID)
RunId = NewType("RunId", UUID)
ProviderConnectionId = NewType("ProviderConnectionId", UUID)

__all__ = [
    "TenantId",
    "UserId",
    "WorkspaceId",
    "FileId",
    "RunId",
    "ProviderConnectionId",
]
