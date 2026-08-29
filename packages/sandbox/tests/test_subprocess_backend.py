"""SubprocessSandbox — dev-only backend behavior."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from vera_core.errors import SandboxTimeoutError
from vera_core.models.code import CodeArtifact
from vera_core.models.ids import RunId
from vera_core.ports.sandbox import DataMount, ResourceLimits
from vera_sandbox.backends.subprocess_backend import SubprocessSandbox

RUN_ID = RunId("00000000-0000-0000-0000-000000000001")


def _artifact(source: str) -> CodeArtifact:
    import hashlib

    return CodeArtifact(source=source, sha256=hashlib.sha256(source.encode()).hexdigest())


async def test_hello_world_succeeds() -> None:
    obs = await SubprocessSandbox().execute(
        script=_artifact("print('hello')"),
        mounts=[],
        limits=ResourceLimits(),
        run_id=RUN_ID,
    )
    assert obs.exit_code == 0
    assert obs.stdout.strip() == "hello"
    assert obs.succeeded


async def test_nonzero_exit_is_captured() -> None:
    obs = await SubprocessSandbox().execute(
        script=_artifact("raise SystemExit(3)"),
        mounts=[],
        limits=ResourceLimits(),
        run_id=RUN_ID,
    )
    assert obs.exit_code == 3
    assert not obs.succeeded


async def test_infinite_loop_times_out() -> None:
    with pytest.raises(SandboxTimeoutError):
        await SubprocessSandbox().execute(
            script=_artifact("import time\ntime.sleep(30)"),
            mounts=[],
            limits=ResourceLimits(timeout_s=5),
            run_id=RUN_ID,
        )


async def test_blocked_import_never_spawns_process(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0
    real = asyncio.create_subprocess_exec

    async def _counting(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        return await real(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _counting)

    obs = await SubprocessSandbox().execute(
        script=_artifact("import socket\nprint(socket)"),
        mounts=[],
        limits=ResourceLimits(),
        run_id=RUN_ID,
    )
    assert calls == 0
    assert obs.exit_code == 1
    assert "socket" in obs.stderr


async def test_mounted_file_is_readable(tmp_path: Path) -> None:
    src = tmp_path / "data.csv"
    src.write_text("x\n1\n2\n")
    obs = await SubprocessSandbox().execute(
        script=_artifact("print(open('data.csv').read().count(chr(10)))"),
        mounts=[DataMount(host_path=str(src), container_path="/w/data.csv")],
        limits=ResourceLimits(),
        run_id=RUN_ID,
    )
    assert obs.exit_code == 0
    assert obs.stdout.strip() == "3"
