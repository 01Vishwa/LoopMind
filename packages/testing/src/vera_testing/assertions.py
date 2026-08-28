"""Shared custom assertions used across VERA test suites."""

from __future__ import annotations

import inspect
from typing import Any

__all__ = ["assert_conforms", "assert_never_contains_secret"]


def assert_conforms(instance: object, protocol: type) -> None:
    """Assert `instance` implements every public method of `protocol`, signature included.

    `typing.runtime_checkable` only compares method names, so a fake can drift
    from its port — a renamed keyword argument, a dropped parameter — and still
    pass `isinstance`. This closes that gap.

    Raises AssertionError naming the first mismatch found.
    """
    for name, expected in inspect.getmembers(protocol, inspect.isfunction):
        if name.startswith("_"):
            continue

        actual = getattr(type(instance), name, None)
        assert actual is not None, (
            f"{type(instance).__name__} is missing {protocol.__name__}.{name}"
        )

        expected_params = _public_params(expected)
        actual_params = _public_params(actual)

        missing = expected_params - actual_params
        assert not missing, (
            f"{type(instance).__name__}.{name} is missing parameters "
            f"required by {protocol.__name__}.{name}: {sorted(missing)}"
        )

        assert inspect.iscoroutinefunction(actual) == inspect.iscoroutinefunction(expected), (
            f"{type(instance).__name__}.{name} async-ness does not match {protocol.__name__}.{name}"
        )


def _public_params(func: Any) -> set[str]:
    """Parameter names of `func`, excluding `self` and `**kwargs`."""
    return {
        name
        for name, param in inspect.signature(func).parameters.items()
        if name != "self" and param.kind is not inspect.Parameter.VAR_KEYWORD
    }


def assert_never_contains_secret(haystack: object, secret: str) -> None:
    """Assert a secret does not appear anywhere in `haystack`'s string form.

    Used to prove BYOK API keys never reach a response body, a log record, or a
    serialised error. A short or empty secret would match trivially, so it is
    rejected outright rather than passing a meaningless check.
    """
    assert len(secret) >= 8, f"secret is too short to check meaningfully: {len(secret)} chars"
    rendered = repr(haystack)
    assert secret not in rendered, (
        f"secret leaked into {type(haystack).__name__}: found at index {rendered.index(secret)}"
    )
