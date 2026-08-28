"""Clock port — injectable time source for deterministic testing."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class ClockPort(Protocol):
    def utcnow(self) -> datetime: ...


class SystemClock:
    """Production implementation — returns real UTC time."""

    def utcnow(self) -> datetime:
        return datetime.now(UTC)


class FixedClock:
    """Test implementation — always returns the same time."""

    def __init__(self, fixed: datetime) -> None:
        self._fixed = fixed

    def utcnow(self) -> datetime:
        return self._fixed


__all__ = ["ClockPort", "SystemClock", "FixedClock"]
