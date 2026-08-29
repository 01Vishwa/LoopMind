"""analyze node — two-step generate/execute/parse with bounded debug retry."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from vera_core.agents._types import AnalyzerScriptOutput, CoderOutput
from vera_core.loop.context import LoopDeps
from vera_core.loop.nodes.analyze import ANALYZER_MAX_DEBUG_ATTEMPTS, analyze
from vera_core.models.file import FileKind, FileRef
from vera_core.models.ids import FileId, TenantId, WorkspaceId
from vera_core.policies import CycleDetector
from vera_core.ports.clock import FixedClock
from vera_core.ports.sandbox import DataMount
from vera_core.prompts import PromptRegistry
from vera_testing.factories.domain import make_agent_defaults, make_run_state
from vera_testing.fakes import FakeEventBus, FakeLLM, FakeRetriever, FakeSandbox

GOOD_STDOUT = (
    "--- Essential Information ---\nrow_count: 3\n"
    "--- Fields ---\n- name=a; dtype=int; samples=1, 2\n"
)


def _ref(name: str = "data.csv") -> FileRef:
    return FileRef(
        file_id=FileId(uuid4()),
        workspace_id=WorkspaceId(uuid4()),
        tenant_id=TenantId(uuid4()),
        filename=name,
        kind=FileKind.CSV,
        size_bytes=10,
        content_sha256="x",
        uri="local",
        created_at=datetime.now(UTC),
    )


def _deps(llm: FakeLLM, sandbox: FakeSandbox, ref: FileRef, tmp_path: Path) -> LoopDeps:
    p = tmp_path / ref.filename
    p.write_bytes(b"a,b,c\n1,2,3\n4,5,6\n")
    return LoopDeps(
        llm=llm,
        sandbox=sandbox,
        retriever=FakeRetriever(),
        event_bus=FakeEventBus(),
        clock=FixedClock(datetime.now(UTC)),
        defaults=make_agent_defaults(),
        registry=PromptRegistry(),
        file_refs=[ref],
        mounts=[DataMount(host_path=str(p), container_path=f"/w/{ref.filename}")],
        cycle_detector=CycleDetector(max_repeats=3),
    )


async def test_happy_path_parses_script_stdout(tmp_path: Path) -> None:
    ref = _ref()
    llm = FakeLLM()
    llm.on("analyzer", AnalyzerScriptOutput(source="print('hi')"))
    sandbox = FakeSandbox()
    sandbox.push_success(stdout=GOOD_STDOUT)

    state = await analyze(make_run_state(), _deps(llm, sandbox, ref, tmp_path))

    assert len(state.descriptions) == 1
    d = state.descriptions[0]
    assert d.partial is False
    assert d.row_count == 3
    assert d.file_id == ref.file_id


async def test_crash_then_debugger_fix_succeeds(tmp_path: Path) -> None:
    ref = _ref()
    llm = FakeLLM()
    llm.on("analyzer", AnalyzerScriptOutput(source="broken("))
    llm.on("debugger", CoderOutput(source="print('fixed')"))
    sandbox = FakeSandbox()
    sandbox.push_failure(stderr="SyntaxError: unexpected EOF")
    sandbox.push_success(stdout=GOOD_STDOUT)

    state = await analyze(make_run_state(), _deps(llm, sandbox, ref, tmp_path))

    assert state.descriptions[0].partial is False
    assert state.descriptions[0].row_count == 3
    assert sandbox.call_count == 2


async def test_exhausts_two_retries_then_partial_fallback(tmp_path: Path) -> None:
    ref = _ref()
    llm = FakeLLM()
    llm.on("analyzer", AnalyzerScriptOutput(source="broken("))
    llm.on("debugger", CoderOutput(source="still broken("))
    llm.on("debugger", CoderOutput(source="broken again("))
    sandbox = FakeSandbox()
    for _ in range(3):
        sandbox.push_failure(stderr="SyntaxError")

    state = await analyze(make_run_state(), _deps(llm, sandbox, ref, tmp_path))

    d = state.descriptions[0]
    assert d.partial is True
    assert [f.name for f in d.schema_fields] == ["a", "b", "c"]  # from the CSV header sample
    assert sandbox.call_count == 1 + ANALYZER_MAX_DEBUG_ATTEMPTS  # 1 + 2
