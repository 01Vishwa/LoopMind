"""ORM models for file descriptions."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import HALFVEC

from vera_db.models.base import Base


class FileDescription(Base):
    __tablename__ = "file_descriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    schema_fields: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    row_count: Mapped[int | None] = mapped_column(Integer)
    sheet_names: Mapped[list[str] | None] = mapped_column(JSONB)
    sample_rows: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    analyzer_script: Mapped[str | None] = mapped_column(Text)
    analyzer_model: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Any | None] = mapped_column(HALFVEC(3072))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

__all__ = ["FileDescription"]
