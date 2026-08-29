"""Cap captured subprocess output at a byte ceiling."""

from __future__ import annotations


def cap_bytes(data: bytes, max_bytes: int) -> tuple[str, bool]:
    """Decode *data* (UTF-8, lossy) truncated to *max_bytes*.

    Returns ``(text, truncated)`` where ``truncated`` is True when bytes were dropped.
    """
    truncated = len(data) > max_bytes
    clipped = data[:max_bytes] if truncated else data
    return clipped.decode("utf-8", errors="replace"), truncated


__all__ = ["cap_bytes"]
