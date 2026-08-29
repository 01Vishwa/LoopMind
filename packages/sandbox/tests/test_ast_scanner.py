"""Deny-list scanner — defense-in-depth, not a security boundary."""

from __future__ import annotations

import pytest
from vera_sandbox.guards.ast_scanner import scan

CLEAN = [
    "import pandas as pd\nprint(pd.DataFrame())",
    "import json, csv, math\nfrom collections import Counter\nprint(1)",
    "x = [i for i in range(10)]\nprint(sum(x))",
]

BLOCKED = [
    ("import socket", "socket"),
    ("from socket import gethostname", "socket"),
    ("import subprocess as sp", "subprocess"),
    ("import ctypes", "ctypes"),
    ("import urllib.request", "urllib"),
    ("import requests", "requests"),
    ("import os\nos.system('ls')", "os.system"),
    ("import os\nos.popen('ls')", "os.popen"),
    ("eval('1+1')", "eval"),
    ("exec('x=1')", "exec"),
    ("__import__('socket')", "__import__"),
]


@pytest.mark.parametrize("source", CLEAN)
def test_clean_scripts_pass(source: str) -> None:
    assert scan(source) is None


@pytest.mark.parametrize(("source", "needle"), BLOCKED)
def test_blocked_scripts_flagged(source: str, needle: str) -> None:
    reason = scan(source)
    assert reason is not None
    assert needle in reason


def test_syntax_error_is_reported_not_raised() -> None:
    reason = scan("def (:\n")
    assert reason is not None
    assert "syntax" in reason.lower()
