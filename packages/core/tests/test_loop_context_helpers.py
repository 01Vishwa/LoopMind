"""read_sample / execute_analyzer_script — the two analyze-node helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from vera_core.loop.context import execute_analyzer_script, read_sample
from vera_core.models.code import CodeArtifact
from vera_core.models.file import FileKind, FileRef
from vera_core.models.ids import FileId, RunId, TenantId, WorkspaceId
from vera_core.ports.sandbox import DataMount
from vera_testing.fakes import FakeSandbox

RID = RunId(uuid4())


def _ref(filename: str, kind: FileKind) -> FileRef:
    return FileRef(
        file_id=FileId(uuid4()),
        workspace_id=WorkspaceId(uuid4()),
        tenant_id=TenantId(uuid4()),
        filename=filename,
        kind=kind,
        size_bytes=10,
        content_sha256="x",
        uri="local",
        created_at=datetime.now(UTC),
    )


def test_read_sample_returns_text_for_csv(tmp_path: Path) -> None:
    p = tmp_path / "payments.csv"
    p.write_bytes(b"a,b\n1,2\n3,4\n")
    mounts = [DataMount(host_path=str(p), container_path="/w/payments.csv")]
    assert read_sample(_ref("payments.csv", FileKind.CSV), mounts, max_bytes=6) == "a,b\n1,"


def test_read_sample_empty_for_binary_kind(tmp_path: Path) -> None:
    p = tmp_path / "book.xlsx"
    p.write_bytes(b"PK\x03\x04rest")
    mounts = [DataMount(host_path=str(p), container_path="/w/book.xlsx")]
    assert read_sample(_ref("book.xlsx", FileKind.XLSX), mounts) == ""


def test_read_sample_empty_when_no_mount_matches() -> None:
    assert read_sample(_ref("missing.csv", FileKind.CSV), []) == ""


async def test_execute_analyzer_script_passes_single_mount_and_30s_limit() -> None:
    sandbox = FakeSandbox()
    sandbox.push_success(stdout="--- Essential Information ---\nrow_count: 2\n")
    mount = DataMount(host_path="/tmp/x.csv", container_path="/w/x.csv")
    obs = await execute_analyzer_script(
        sandbox, CodeArtifact(source="print(1)", sha256="s"), mount, RID
    )
    assert obs.succeeded
    assert sandbox.last_call["mounts"] == [mount]
    assert sandbox.last_call["limits"].timeout_s == 30


async def test_execute_analyzer_script_converts_timeout_to_failed_observation() -> None:
    sandbox = FakeSandbox()
    sandbox.push_timeout()
    obs = await execute_analyzer_script(
        sandbox,
        CodeArtifact(source="x", sha256="s"),
        DataMount(host_path="/tmp/x", container_path="/w/x"),
        RID,
    )
    assert obs.exit_code == 124
    assert not obs.succeeded
