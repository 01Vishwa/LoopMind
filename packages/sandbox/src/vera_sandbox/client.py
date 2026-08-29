"""Fail-closed factory for sandbox backends.

The subprocess backend is dev-only and must be explicitly opted into with
``VERA_SANDBOX_ALLOW_SUBPROCESS=1``. Absent that, requesting it raises
:class:`SandboxNotAvailableError` — the system fails closed rather than running
model-generated code un-isolated. Real backends are not implemented yet.

When ``apps/api`` grows a composition root (``container.py``), the environment
gate moves there; for now it lives here because nothing else constructs a
sandbox.
"""

from __future__ import annotations

import os
from typing import Literal

from vera_core.errors import SandboxNotAvailableError
from vera_core.ports.sandbox import SandboxPort

from vera_sandbox.backends.subprocess_backend import SubprocessSandbox

Backend = Literal["subprocess", "docker", "gvisor"]

_ALLOW_ENV = "VERA_SANDBOX_ALLOW_SUBPROCESS"


class SandboxClient:
    """Callable factory: ``SandboxClient("subprocess")`` returns a ``SandboxPort``."""

    def __new__(cls, backend: Backend) -> SandboxPort:  # type: ignore[misc]
        if backend == "subprocess":
            if os.environ.get(_ALLOW_ENV) != "1":
                raise SandboxNotAvailableError(
                    "subprocess sandbox is dev-only; set "
                    f"{_ALLOW_ENV}=1 to enable it in this environment"
                )
            return SubprocessSandbox()
        if backend in ("docker", "gvisor"):
            raise NotImplementedError(f"{backend!r} sandbox backend is not implemented yet")
        raise ValueError(f"unknown sandbox backend {backend!r}")


__all__ = ["Backend", "SandboxClient"]
