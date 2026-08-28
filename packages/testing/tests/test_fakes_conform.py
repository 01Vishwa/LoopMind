"""Every fake satisfies the vera_core port protocol it stands in for."""

from __future__ import annotations

import inspect

import pytest
from vera_core.ports import (
    EventBusPort,
    KeyVaultPort,
    LLMPort,
    ObjectStorePort,
    SandboxPort,
)
from vera_testing.assertions import assert_conforms
from vera_testing.fakes import (
    FakeEventBus,
    FakeKeyVault,
    FakeLLM,
    FakeObjectStore,
    FakeSandbox,
)

PAIRS = [
    (FakeLLM, LLMPort),
    (FakeKeyVault, KeyVaultPort),
    (FakeSandbox, SandboxPort),
    (FakeObjectStore, ObjectStorePort),
    (FakeEventBus, EventBusPort),
]


@pytest.mark.parametrize(
    ("fake_cls", "protocol"), PAIRS, ids=lambda p: getattr(p, "__name__", str(p))
)
def test_fake_is_runtime_instance_of_protocol(fake_cls, protocol):
    assert isinstance(fake_cls(), protocol)


@pytest.mark.parametrize(
    ("fake_cls", "protocol"), PAIRS, ids=lambda p: getattr(p, "__name__", str(p))
)
def test_fake_signatures_match_protocol(fake_cls, protocol):
    """runtime_checkable only checks method *names*. Check the signatures too."""
    assert_conforms(fake_cls(), protocol)


def test_every_port_method_is_keyword_only():
    """Convention: ports take keyword-only arguments so call sites stay readable."""
    for _, protocol in PAIRS:
        for name, member in inspect.getmembers(protocol, inspect.isfunction):
            if name.startswith("_"):
                continue
            params = list(inspect.signature(member).parameters.values())[1:]  # drop self
            positional = [p.name for p in params if p.kind is not inspect.Parameter.KEYWORD_ONLY]
            assert not positional, (
                f"{protocol.__name__}.{name} has positional parameters: {positional}"
            )
