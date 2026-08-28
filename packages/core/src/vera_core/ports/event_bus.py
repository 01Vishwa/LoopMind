"""Event bus port — run event publication and consumption."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vera_core.models.events import RunEvent
from vera_core.models.ids import RunId


@runtime_checkable
class EventBusPort(Protocol):
    """Emit and consume run events. Sequence numbers are monotonically increasing per run."""

    async def emit(self, *, run_id: RunId, event: RunEvent) -> int:
        """Store event and return its sequence number."""
        ...

    async def read_from(
        self,
        *,
        run_id: RunId,
        after_seq: int,
    ) -> list[tuple[int, RunEvent]]:
        """Return all events after after_seq as (seq, event) pairs."""
        ...


__all__ = ["EventBusPort"]
