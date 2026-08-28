"""``vera doctor`` — environment and Supabase readiness checks."""

from __future__ import annotations

import asyncio
import os
from typing import Annotated

import httpx
import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy import text
from vera_core.models.provider import ProviderKind
from vera_db import build_direct_engine
from vera_llm import PROVIDER_CONFIGS, validate_connection

_console = Console(width=160)

_DB_ENV = ("VERA_DATABASE_URL", "VERA_DATABASE_URL_DIRECT")
_PROVIDER_ENV = {
    ProviderKind.OPENROUTER: "OPENROUTER_API_KEY",
    ProviderKind.NVIDIA_NIM: "NVIDIA_API_KEY",
}

_CHECKS = (
    ("select 1", "select 1"),
    (
        "supabase_vault extension",
        "select exists(select 1 from pg_extension where extname = 'supabase_vault')",
    ),
    (
        "public.current_tenant_id()",
        "select exists(select 1 from pg_proc where proname = 'current_tenant_id')",
    ),
)


async def _db_checks() -> list[tuple[str, bool, str]]:
    url = os.environ["VERA_DATABASE_URL_DIRECT"]
    engine = build_direct_engine(url)
    results: list[tuple[str, bool, str]] = []
    try:
        async with engine.connect() as conn:
            for label, sql in _CHECKS:
                try:
                    value = (await conn.execute(text(sql))).scalar()
                    ok = value in (1, True)
                    results.append((label, ok, "" if ok else f"returned {value!r}"))
                except Exception as exc:  # noqa: BLE001 - report, do not crash
                    results.append((label, False, str(exc)))
    except Exception as exc:  # noqa: BLE001
        results.append(("database connection", False, str(exc)))
    finally:
        await engine.dispose()
    return results


async def _provider_checks() -> list[tuple[str, bool, str]]:
    results: list[tuple[str, bool, str]] = []
    async with httpx.AsyncClient() as http:
        for kind, env in _PROVIDER_ENV.items():
            key = os.environ.get(env)
            if not key:
                results.append((f"provider {kind.value}", True, "skipped (no key in env)"))
                continue
            res = await validate_connection(
                kind=kind,
                base_url=PROVIDER_CONFIGS[kind].default_base_url,
                api_key=key,
                http=http,
            )
            results.append((f"provider {kind.value}", res.valid, res.error or ""))
    return results


async def _run(check_providers: bool) -> list[tuple[str, bool, str]]:
    results: list[tuple[str, bool, str]] = []
    env_ok = True
    for var in _DB_ENV:
        present = bool(os.environ.get(var))
        env_ok = env_ok and present
        results.append((f"env {var}", present, "" if present else "not set"))
    if env_ok:
        results.extend(await _db_checks())
        if check_providers:
            results.extend(await _provider_checks())
    return results


def doctor(
    check_providers: Annotated[
        bool,
        typer.Option("--check-providers", help="Also ping configured provider /models endpoints"),
    ] = False,
) -> None:
    """Verify env vars and Supabase Postgres are ready; exit 1 on any failure."""
    results = asyncio.run(_run(check_providers))
    table = Table(title="vera doctor")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")
    for label, ok, detail in results:
        table.add_row(label, "[green]ok[/green]" if ok else "[red]FAIL[/red]", detail)
    _console.print(table)
    failed = sum(1 for _, ok, _ in results if not ok)
    typer.echo(f"event=doctor checks={len(results)} failed={failed}")
    if failed:
        raise typer.Exit(1)


__all__ = ["doctor"]
