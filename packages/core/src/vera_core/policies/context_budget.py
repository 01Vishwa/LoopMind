"""Context budget policy — tracks token usage against a limit."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ContextBudget:
    """Tracks cumulative token usage and checks whether a budget is exceeded.

    Agents call ``consume()`` after each LLM call and check ``is_exceeded()``
    before proceeding to the next step.
    """

    max_tokens: int
    _used: int = field(default=0, init=False)

    def consume(self, tokens: int) -> None:
        """Record token consumption."""
        if tokens < 0:
            raise ValueError(f"Token count must be non-negative, got {tokens}")
        self._used += tokens

    @property
    def used(self) -> int:
        return self._used

    @property
    def remaining(self) -> int:
        return max(0, self.max_tokens - self._used)

    def is_exceeded(self) -> bool:
        return self._used >= self.max_tokens

    def __repr__(self) -> str:
        return f"ContextBudget(used={self._used}, max={self.max_tokens})"


__all__ = ["ContextBudget"]
