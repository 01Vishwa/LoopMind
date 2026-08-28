"""MemoryEventBus — in-memory event bus for tests."""

from __future__ import annotations

from vera_core.models.events import RunEvent
from vera_core.models.ids import RunId


class MemoryEventBus:
    """Stores events in-memory. Sequence numbers start at 1 per run."""

    def __init__(self) -> None:
        # run_id (str) -> list of (seq, event)
        self._events: dict[str, list[tuple[int, RunEvent]]] = {}

    async def emit(self, *, run_id: RunId, event: RunEvent) -> int:
        key = str(run_id)
        if key not in self._events:
            self._events[key] = []
        seq = len(self._events[key]) + 1
        self._events[key].append((seq, event))
        return seq

    async def read_from(
        self,
        *,
        run_id: RunId,
        after_seq: int,
    ) -> list[tuple[int, RunEvent]]:
        key = str(run_id)
        all_events = self._events.get(key, [])
        return [(seq, evt) for seq, evt in all_events if seq > after_seq]

    def all_events(self, run_id: RunId) -> list[RunEvent]:
        """Return all events for a run (for assertions)."""
        return [evt for _, evt in self._events.get(str(run_id), [])]

    def event_count(self, run_id: RunId) -> int:
        return len(self._events.get(str(run_id), []))


__all__ = ["MemoryEventBus"]
