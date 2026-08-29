"""Pure parsing of the two-step Analyzer's script stdout into a FileDescription.

No I/O, no LLM, no sandbox. :func:`parse_analyzer_stdout` handles the success
path; :func:`build_partial_description` is the fallback when the script never
produced usable output (crashed twice, or timed out).
"""

from __future__ import annotations

import json
import re
from typing import Any

from vera_core.models.file import FileDescription, SchemaField
from vera_core.models.ids import FileId

_SUMMARY_CAP = 8192
_HEADER_RE = re.compile(r"^--- .+ ---\s*$")
_ROW_COUNT_RE = re.compile(r"^row_count:\s*(\d+)\s*$")
_SHEETS_RE = re.compile(r"^sheet_names:\s*(.+)$")


def _section(lines: list[str], name: str) -> list[str]:
    """Lines strictly between ``--- {name} ---`` and the next ``--- ... ---`` header."""
    out: list[str] = []
    collecting = False
    for line in lines:
        if _HEADER_RE.match(line):
            collecting = line.strip().strip("- ").strip() == name
            continue
        if collecting:
            out.append(line)
    return out


def _parse_field_line(line: str) -> SchemaField | None:
    body = line.strip()
    if body.startswith("- "):
        body = body[2:]
    parts = dict(p.split("=", 1) for p in body.split("; ") if "=" in p)
    if "name" not in parts:
        return None
    samples = [s.strip() for s in parts.get("samples", "").split(",") if s.strip()]
    return SchemaField(
        name=parts["name"].strip(),
        dtype=parts.get("dtype", "unknown").strip() or "unknown",
        sample_values=samples,
    )


def parse_analyzer_stdout(file_id: FileId, stdout: str) -> FileDescription:
    """Parse the analyzer script's structured stdout. Best-effort, never raises."""
    lines = stdout.splitlines()

    row_count: int | None = None
    sheet_names: list[str] | None = None
    for line in lines:
        stripped = line.strip()
        if row_count is None and (m := _ROW_COUNT_RE.match(stripped)):
            row_count = int(m.group(1))
        if sheet_names is None and (m := _SHEETS_RE.match(stripped)):
            sheet_names = [s.strip() for s in m.group(1).split(",") if s.strip()] or None

    fields = [f for line in _section(lines, "Fields") if (f := _parse_field_line(line))]

    rows: list[dict[str, Any]] = []
    for line in _section(lines, "Sample Rows"):
        candidate = line.strip()
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
        except (ValueError, TypeError):
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)

    return FileDescription(
        file_id=file_id,
        summary_text=stdout[:_SUMMARY_CAP],
        schema_fields=fields,
        row_count=row_count,
        sheet_names=sheet_names,
        sample_rows=rows or None,
        partial=False,
    )


def _looks_like_json(sample: str) -> bool:
    return sample.lstrip().startswith(("{", "["))


def build_partial_description(file_id: FileId, sample: str) -> FileDescription:
    """Columns-only best-effort description from a raw file sample. ``partial=True``."""
    names: list[str] = []
    stripped = sample.strip()

    if _looks_like_json(stripped):
        try:
            parsed: Any = json.loads(stripped)
        except (ValueError, TypeError):
            parsed = None
        if isinstance(parsed, dict):
            names = list(parsed.keys())
        elif isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
            seen: dict[str, None] = {}
            for item in parsed:
                if isinstance(item, dict):
                    for key in item:
                        seen.setdefault(key, None)
            names = list(seen)
    else:
        first = next((ln for ln in sample.splitlines() if ln.strip()), "")
        if first and ("," in first or "\t" in first) and not any(c in first for c in "{}"):
            sep = "\t" if "\t" in first else ","
            names = [c.strip() for c in first.split(sep) if c.strip()]

    return FileDescription(
        file_id=file_id,
        summary_text=(
            "Partial description — the analyzer script failed after retries. "
            f"Best-effort from the first {min(len(sample), 2000)} bytes:\n{sample[:2000]}"
        ),
        schema_fields=[SchemaField(name=n, dtype="unknown") for n in names],
        row_count=None,
        partial=True,
    )


__all__ = ["build_partial_description", "parse_analyzer_stdout"]
