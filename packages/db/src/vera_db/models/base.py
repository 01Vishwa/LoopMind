"""Declarative base and shared column mixins."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Root declarative base for all VERA ORM models."""


class TimestampMixin:
    """Adds a server-defaulted ``created_at`` column."""

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


__all__ = ["Base", "TimestampMixin"]
