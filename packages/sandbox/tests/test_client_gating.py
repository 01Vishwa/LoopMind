"""SandboxClient fail-closed gating."""

from __future__ import annotations

import pytest
from vera_core.errors import SandboxNotAvailableError
from vera_sandbox.backends.subprocess_backend import SubprocessSandbox
from vera_sandbox.client import SandboxClient


def test_subprocess_refused_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VERA_SANDBOX_ALLOW_SUBPROCESS", raising=False)
    with pytest.raises(SandboxNotAvailableError):
        SandboxClient("subprocess")


def test_subprocess_allowed_with_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERA_SANDBOX_ALLOW_SUBPROCESS", "1")
    sandbox = SandboxClient("subprocess")
    assert isinstance(sandbox, SubprocessSandbox)


def test_docker_backend_not_implemented(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERA_SANDBOX_ALLOW_SUBPROCESS", "1")
    with pytest.raises(NotImplementedError):
        SandboxClient("docker")


def test_gvisor_backend_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        SandboxClient("gvisor")


def test_unknown_backend_rejected() -> None:
    with pytest.raises(ValueError):
        SandboxClient("banana")  # type: ignore[arg-type]
