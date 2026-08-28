"""ORM models for the provider tables (mirrors 0003_providers.sql)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vera_db.models.base import Base

_KIND_VALUES = ("openrouter", "nvidia_nim")
_STATUS_VALUES = ("connected", "validating", "failed", "revoked")


class ProviderConnectionRow(Base):
    __tablename__ = "provider_connections"
    __table_args__ = (
        UniqueConstraint("user_id", "display_name"),
        CheckConstraint(
            "kind in ('openrouter','nvidia_nim')", name="provider_connections_kind_check"
        ),
        CheckConstraint(
            "status in ('connected','validating','failed','revoked')",
            name="provider_connections_status_check",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(Text)
    display_name: Mapped[str] = mapped_column(Text)
    base_url: Mapped[str] = mapped_column(Text)
    api_key_ref: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, server_default="validating")
    last_validated_at: Mapped[datetime | None] = mapped_column(default=None)
    last_error: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    models: Mapped[list[ProviderModelCacheRow]] = relationship(
        back_populates="connection",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ProviderModelCacheRow(Base):
    __tablename__ = "provider_models_cache"

    provider_connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("provider_connections.id", ondelete="CASCADE"),
        primary_key=True,
    )
    model_id: Mapped[str] = mapped_column(Text, primary_key=True)
    display_name: Mapped[str] = mapped_column(Text)
    context_window: Mapped[int] = mapped_column(Integer, server_default="0")
    input_price_per_m: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), default=None)
    output_price_per_m: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), default=None)
    supports_json_mode: Mapped[bool] = mapped_column(Boolean, server_default="false")
    supports_function_calling: Mapped[bool] = mapped_column(Boolean, server_default="false")
    supports_vision: Mapped[bool] = mapped_column(Boolean, server_default="false")
    cached_at: Mapped[datetime] = mapped_column(server_default=func.now())

    connection: Mapped[ProviderConnectionRow] = relationship(back_populates="models")


__all__ = ["ProviderConnectionRow", "ProviderModelCacheRow"]
