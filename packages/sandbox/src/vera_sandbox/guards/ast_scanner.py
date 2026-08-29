"""Static deny-list scan of model-generated Python.

**This is not a security boundary.** ``getattr`` chains, dunder traversal, and
string obfuscation all bypass it trivially. The real isolation boundary is the
container / microVM backend (Phase 4 proper). This scan is defense-in-depth: it
catches the obvious, cheap-to-detect cases before a subprocess is ever spawned,
and it turns them into a normal failed ``Observation`` the Debugger can react to.
"""

from __future__ import annotations

import ast

# Import roots that have no place in a data-analysis script.
_DENIED_MODULES: frozenset[str] = frozenset(
    {
        "socket",
        "subprocess",
        "ctypes",
        "multiprocessing",
        "resource",
        "urllib",
        "urllib2",
        "requests",
        "httpx",
        "aiohttp",
        "http",
        "ftplib",
        "telnetlib",
        "smtplib",
        "asyncio.subprocess",
        "pty",
        "fcntl",
    }
)

# Bare builtins that enable arbitrary execution / import.
_DENIED_NAMES: frozenset[str] = frozenset({"eval", "exec", "compile", "__import__"})

# ``os`` attributes that shell out or replace the process image.
_DENIED_OS_ATTRS: tuple[str, ...] = ("system", "popen", "fork", "forkpty")
_DENIED_OS_PREFIXES: tuple[str, ...] = ("exec", "spawn", "posix_spawn")


def _root(module: str) -> str:
    return module.split(".", 1)[0]


def _dotted(node: ast.Attribute) -> str | None:
    parts: list[str] = [node.attr]
    cur: ast.expr = node.value
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        return ".".join(reversed(parts))
    return None


def scan(source: str) -> str | None:
    """Return a human-readable reason if *source* uses a denied construct, else None."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:  # surfaced, never raised past the sandbox
        return f"syntax error: {exc.msg}"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in _DENIED_MODULES or _root(alias.name) in _DENIED_MODULES:
                    return f"import of blocked module {alias.name!r}"
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod in _DENIED_MODULES or _root(mod) in _DENIED_MODULES:
                return f"import from blocked module {mod!r}"
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in _DENIED_NAMES:
                return f"call to blocked builtin {func.id!r}"
            if isinstance(func, ast.Attribute):
                dotted = _dotted(func)
                if dotted is None:
                    continue
                head, _, tail = dotted.partition(".")
                if head == "os" and (
                    func.attr in _DENIED_OS_ATTRS or func.attr.startswith(_DENIED_OS_PREFIXES)
                ):
                    return f"call to blocked function {dotted!r}"
                if _root(dotted) in _DENIED_MODULES:
                    return f"call into blocked module {dotted!r}"
    return None


__all__ = ["scan"]
