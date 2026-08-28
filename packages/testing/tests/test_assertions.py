"""Tests for the custom assertions — they must fail when they should."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import pytest
from vera_testing.assertions import assert_conforms, assert_never_contains_secret


@runtime_checkable
class _ExamplePort(Protocol):
    async def fetch(self, *, key: str, limit: int) -> str: ...


class _Good:
    async def fetch(self, *, key: str, limit: int) -> str:
        return key * limit


class _MissingParam:
    async def fetch(self, *, key: str) -> str:
        return key


class _NotAsync:
    def fetch(self, *, key: str, limit: int) -> str:
        return key


class _MissingMethod:
    pass


def test_conforms_accepts_a_matching_implementation():
    assert_conforms(_Good(), _ExamplePort)


def test_conforms_rejects_a_dropped_parameter():
    with pytest.raises(AssertionError, match="missing parameters.*limit"):
        assert_conforms(_MissingParam(), _ExamplePort)


def test_conforms_rejects_a_sync_implementation_of_an_async_port():
    with pytest.raises(AssertionError, match="async-ness"):
        assert_conforms(_NotAsync(), _ExamplePort)


def test_conforms_rejects_a_missing_method():
    with pytest.raises(AssertionError, match="is missing"):
        assert_conforms(_MissingMethod(), _ExamplePort)


def test_secret_check_passes_when_absent():
    assert_never_contains_secret({"api_key_masked": "sk-or-v1-****"}, "sk-or-v1-abc12345")


def test_secret_check_fails_when_present():
    with pytest.raises(AssertionError, match="leaked"):
        assert_never_contains_secret({"api_key": "sk-or-v1-abc12345"}, "sk-or-v1-abc12345")


def test_secret_check_rejects_a_trivially_short_secret():
    with pytest.raises(AssertionError, match="too short"):
        assert_never_contains_secret({"a": "b"}, "abc")
