"""File and workspace domain models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from vera_core.models.ids import FileId, TenantId, WorkspaceId


class FileKind(StrEnum):
    CSV = "csv"
    XLSX = "xlsx"
    JSON = "json"
    PARQUET = "parquet"
    MARKDOWN = "md"
    TXT = "txt"
    PDF = "pdf"
    SQLITE = "sqlite"
    ZIP = "zip"


class SchemaField(BaseModel):
    name: str
    dtype: str
    nullable: bool = True
    sample_values: list[Any] = Field(default_factory=list)

    model_config = {"frozen": True}


class FileRef(BaseModel):
    """Lightweight file record — stored in the files table."""

    file_id: FileId
    workspace_id: WorkspaceId
    tenant_id: TenantId
    filename: str
    kind: FileKind
    size_bytes: int
    content_sha256: str
    uri: str  # local: .vera/objects/<sha256> or presigned URL
    created_at: datetime

    model_config = {"frozen": True}


class FileDescription(BaseModel):
    """Rich description of a file produced by the Analyzer agent."""

    file_id: FileId
    summary_text: str = Field(max_length=8192)  # capped at 8 KB for prompt safety
    schema_fields: list[SchemaField] = Field(default_factory=list)
    row_count: int | None = None
    sheet_names: list[str] | None = None
    sample_rows: list[dict[str, Any]] | None = None
    generated_by_script_sha: str = ""
    partial: bool = False  # True when built by the sample-only fallback (analyzer script failed)
    analyzer_model: str = ""
    prompt_version: str = "v1"
    # embedding excluded from default serialisation; loaded separately
    embedding: list[float] | None = Field(default=None, exclude=True)

    model_config = {"frozen": True}


__all__ = ["FileKind", "SchemaField", "FileRef", "FileDescription"]
