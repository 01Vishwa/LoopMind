"""Dev-only sandbox backend: run the script as a plain child ``python`` process.

Isolation here is weak by design — an AST deny-list, a temp CWD with only the
mounted files copied in, best-effort POSIX rlimits, and a hard wall-clock
timeout. It exists so the Analyzer loop is runnable end-to-end in dev and CI.
Production isolation is the container / microVM backend, not this.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

from vera_core.errors import SandboxTimeoutError
from vera_core.models.code import CodeArtifact
from vera_core.models.ids import RunId
from vera_core.models.observation import Observation
from vera_core.ports.sandbox import DataMount, ResourceLimits

from vera_sandbox.capture import cap_bytes
from vera_sandbox.guards.ast_scanner import scan
from vera_sandbox.guards.resource_limits import rlimit_preexec
from vera_sandbox.mounts import cleanup, materialize

_SCRIPT_NAME = "__vera_script.py"


class SubprocessSandbox:
    """Implements :class:`vera_core.ports.sandbox.SandboxPort` via a child process."""

    async def execute(
        self,
        *,
        script: CodeArtifact,
        mounts: list[DataMount],
        limits: ResourceLimits,
        run_id: RunId,
    ) -> Observation:
        blocked = scan(script.source)
        if blocked is not None:
            return Observation(
                stdout="",
                stderr=f"Blocked: {blocked}",
                exit_code=1,
                duration_ms=0,
            )

        workdir = materialize(mounts)
        script_path = Path(workdir) / _SCRIPT_NAME
        script_path.write_text(script.source, encoding="utf-8")
        preexec = rlimit_preexec(limits.memory_mb, limits.timeout_s)

        started = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_exec(
                _python_exe(),
                str(script_path),
                cwd=workdir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=preexec,
            )
            try:
                out, err = await asyncio.wait_for(proc.communicate(), timeout=limits.timeout_s)
            except TimeoutError as exc:
                proc.kill()
                await proc.wait()
                raise SandboxTimeoutError(
                    f"script exceeded {limits.timeout_s}s wall-clock limit"
                ) from exc

            duration_ms = int((time.monotonic() - started) * 1000)
            stdout, out_trunc = cap_bytes(out, limits.max_output_bytes)
            stderr, err_trunc = cap_bytes(err, limits.max_output_bytes)
            return Observation(
                stdout=stdout,
                stderr=stderr,
                exit_code=proc.returncode if proc.returncode is not None else 0,
                duration_ms=duration_ms,
                truncated=out_trunc or err_trunc,
            )
        finally:
            cleanup(workdir)


def _python_exe() -> str:
    import sys

    return sys.executable


__all__ = ["SubprocessSandbox"]
