"""VERA sandbox — untrusted code execution backends and static guards."""

from __future__ import annotations

from vera_sandbox.backends.subprocess_backend import SubprocessSandbox
from vera_sandbox.client import Backend, SandboxClient

__all__ = ["Backend", "SandboxClient", "SubprocessSandbox"]
