"""Cycle detection policy — detects repeated identical plans.

If the planner generates the same plan text twice in a row, the loop is
stuck. We detect this and force termination to avoid infinite loops.
"""

from __future__ import annotations

import hashlib
import json

from vera_core.models.plan import PlanStep


def plan_fingerprint(steps: list[PlanStep]) -> str:
    """Return a stable hash of the active plan text.

    Steps are sorted by index and serialised as JSON before hashing.
    """
    active = sorted([s for s in steps if not s.superseded], key=lambda s: s.index)
    payload = json.dumps([s.text for s in active], sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


class CycleDetector:
    """Tracks plan fingerprints across rounds.

    A cycle is detected when the same fingerprint appears twice consecutively.
    """

    def __init__(self, max_repeats: int = 2) -> None:
        self._max_repeats = max_repeats
        self._history: list[str] = []

    def record(self, steps: list[PlanStep]) -> None:
        """Record the current plan for cycle detection."""
        self._history.append(plan_fingerprint(steps))

    def is_cycling(self) -> bool:
        """Return True if the last max_repeats plans are identical."""
        if len(self._history) < self._max_repeats:
            return False
        tail = self._history[-self._max_repeats :]
        return len(set(tail)) == 1

    @property
    def history(self) -> list[str]:
        return list(self._history)


__all__ = ["plan_fingerprint", "CycleDetector"]
