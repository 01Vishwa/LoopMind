"""Mount materialization and output capping."""

from __future__ import annotations

from pathlib import Path

from vera_core.ports.sandbox import DataMount
from vera_sandbox.capture import cap_bytes
from vera_sandbox.mounts import cleanup, materialize


def test_materialize_copies_files_by_basename(tmp_path: Path) -> None:
    src = tmp_path / "payments.csv"
    src.write_text("a,b\n1,2\n")
    mounts = [DataMount(host_path=str(src), container_path="/data/payments.csv")]

    workdir = materialize(mounts)
    try:
        copied = Path(workdir) / "payments.csv"
        assert copied.is_file()
        assert copied.read_text() == "a,b\n1,2\n"
        assert copied.resolve() != src.resolve()
    finally:
        cleanup(workdir)
    assert not Path(workdir).exists()


def test_cap_bytes_truncates_and_flags() -> None:
    text, truncated = cap_bytes(b"hello world", 5)
    assert text == "hello"
    assert truncated is True


def test_cap_bytes_passes_short_output() -> None:
    text, truncated = cap_bytes(b"hi", 1024)
    assert text == "hi"
    assert truncated is False
