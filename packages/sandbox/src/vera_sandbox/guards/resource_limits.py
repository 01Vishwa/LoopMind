"""Best-effort POSIX resource caps applied in the child before ``exec``.

On Windows (common dev environment here) there is no ``resource`` module, so
this is inert and the ``asyncio.wait_for`` timeout is the only real guard. That
is a known, documented limitation of the dev-only subprocess backend.
"""

from __future__ import annotations

import sys
from collections.abc import Callable


def rlimit_preexec(memory_mb: int, cpu_seconds: int) -> Callable[[], None] | None:
    """Return a ``preexec_fn`` that caps address space and CPU time, or None
    when the platform has no ``resource`` module."""
    if sys.platform == "win32":
        return None

    def _apply() -> None:
        import resource

        mem_bytes = memory_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        # Hard CPU ceiling a hair above the wall-clock timeout as a backstop.
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds + 1, cpu_seconds + 1))

    return _apply


__all__ = ["rlimit_preexec"]
