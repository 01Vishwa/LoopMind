"""DS-STAR loop nodes — one pure async function per file, one event each."""

from __future__ import annotations

from vera_core.loop.context import max_active_index, numbered
from vera_core.loop.nodes.analyze import analyze
from vera_core.loop.nodes.code import code
from vera_core.loop.nodes.debug import debug
from vera_core.loop.nodes.execute import execute
from vera_core.loop.nodes.finalize import finalize
from vera_core.loop.nodes.plan import plan
from vera_core.loop.nodes.retrieve import retrieve
from vera_core.loop.nodes.route import route
from vera_core.loop.nodes.truncate import truncate
from vera_core.loop.nodes.verify import verify

__all__ = [
    "analyze",
    "code",
    "debug",
    "execute",
    "finalize",
    "max_active_index",
    "numbered",
    "plan",
    "retrieve",
    "route",
    "truncate",
    "verify",
]
