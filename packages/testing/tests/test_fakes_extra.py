"""Phase 3 additions to the test doubles: .on(), FakeRetriever, push_observation."""

from __future__ import annotations

from vera_core.models.verdict import Verdict
from vera_core.ports import RetrieverPort
from vera_core.ports.sandbox import ResourceLimits
from vera_testing.factories.domain import (
    make_code_artifact,
    make_file_description,
    make_observation,
)
from vera_testing.fakes import FakeLLM, FakeRetriever, FakeSandbox


async def test_fake_llm_on_routes_by_agent():
    llm = FakeLLM()
    llm.push_response("global")
    llm.on("verifier", Verdict(sufficient=True, reason="all good here"))

    v = await llm.complete(
        provider_connection_id=None,
        model_id="m",
        messages=[],
        response_schema=Verdict,
        agent="verifier",
    )
    assert v.parsed is not None
    assert v.parsed.sufficient is True

    g = await llm.complete(provider_connection_id=None, model_id="m", messages=[], agent="coder")
    assert g.content == "global"


async def test_fake_llm_on_falls_back_to_global_when_agent_queue_drained():
    llm = FakeLLM()
    llm.on("verifier", Verdict(sufficient=False, reason="not yet complete"))
    llm.push_response("fallback")

    first = await llm.complete(
        provider_connection_id=None, model_id="m", messages=[], agent="verifier"
    )
    assert first.parsed is not None and first.parsed.sufficient is False

    second = await llm.complete(
        provider_connection_id=None, model_id="m", messages=[], agent="verifier"
    )
    assert second.content == "fallback"


async def test_fake_retriever_returns_top_k():
    r = FakeRetriever([make_file_description() for _ in range(5)])
    out = await r.search(query="q", workspace_id=None, top_k=3)
    assert len(out) == 3
    assert isinstance(r, RetrieverPort)


async def test_fake_retriever_set_results():
    r = FakeRetriever()
    assert await r.search(query="q", workspace_id=None) == []
    r.set_results([make_file_description(), make_file_description()])
    assert len(await r.search(query="q", workspace_id=None)) == 2


async def test_fake_sandbox_push_observation():
    sb = FakeSandbox()
    sb.push_observation(make_observation(stdout="hi"))
    obs = await sb.execute(
        script=make_code_artifact(),
        mounts=[],
        limits=ResourceLimits(),
        run_id=None,
    )
    assert obs.stdout == "hi"
