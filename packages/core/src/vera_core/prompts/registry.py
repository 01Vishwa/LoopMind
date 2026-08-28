"""Versioned Jinja prompt templates resolved by agent name."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, StrictUndefined

_DEFAULT_DIR = Path(__file__).parent / "templates"
_VERSION_RE = re.compile(r"^v(\d+)\.jinja$")
_ENV = Environment(
    undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True, autoescape=False
)


@dataclass(frozen=True)
class PromptTemplate:
    agent: str
    version: str
    source: str
    sha256: str

    def render(self, **variables: object) -> str:
        return _ENV.from_string(self.source).render(**variables)


class PromptRegistry:
    def __init__(self, templates_dir: Path | None = None) -> None:
        self._dir = templates_dir or _DEFAULT_DIR

    def _versions(self, agent: str) -> dict[str, Path]:
        agent_dir = self._dir / agent
        out: dict[str, Path] = {}
        if agent_dir.is_dir():
            for p in agent_dir.iterdir():
                m = _VERSION_RE.match(p.name)
                if m and p.stat().st_size > 0:
                    out[f"v{int(m.group(1))}"] = p
        return out

    def list_versions(self, agent: str) -> list[str]:
        return sorted(self._versions(agent), key=lambda v: int(v[1:]))

    def get(self, agent: str, version: str | None = None) -> PromptTemplate:
        versions = self._versions(agent)
        if not versions:
            raise KeyError(f"No prompt templates for agent {agent!r}")
        chosen = version or self.list_versions(agent)[-1]
        path = versions[chosen]
        source = path.read_text(encoding="utf-8")
        return PromptTemplate(agent, chosen, source, hashlib.sha256(source.encode()).hexdigest())


__all__ = ["PromptRegistry", "PromptTemplate"]
