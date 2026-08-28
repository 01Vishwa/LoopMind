"""Mask API keys for display — never reveal more than a short prefix."""

from __future__ import annotations


def mask_key(key: str) -> str:
    """Return the first 8 characters followed by ``****``; fully masked if short."""
    if len(key) < 12:
        return "****"
    return f"{key[:8]}****"


__all__ = ["mask_key"]
