"""``vera provider`` — connect, list, validate, and remove BYOK provider connections."""

from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import UUID

import typer
from rich.console import Console
from rich.table import Table
from vera_core.errors import VeraError
from vera_core.models.ids import ProviderConnectionId, TenantId, UserId
from vera_core.models.provider import ProviderKind

from vera_cli.constants import DEV_TENANT_ID, DEV_USER_ID
from vera_cli.deps import aclose, build_deps
from vera_cli.masking import mask_key
from vera_cli.services.provider_service import ProviderService

provider_app = typer.Typer(no_args_is_help=True, help="Manage BYOK model-provider connections.")
_console = Console(width=160)

_ENV_BY_KIND = {
    ProviderKind.OPENROUTER: "OPENROUTER_API_KEY",
    ProviderKind.NVIDIA_NIM: "NVIDIA_API_KEY",
}


@asynccontextmanager
async def _provider_service() -> AsyncIterator[ProviderService]:
    """Build a session-backed ``ProviderService`` from live dependencies.

    Tests monkeypatch this to yield a fake-backed service.
    """
    from vera_db import ProviderRepository, VaultRepository
    from vera_llm import LLMClient

    deps = await build_deps()
    try:
        async with deps.sessionmaker() as session:
            repo = ProviderRepository(session=session)
            vault = VaultRepository(session=session)
            llm = LLMClient(key_vault=vault, provider_repo=repo, http=deps.http)
            yield ProviderService(repo=repo, vault=vault, validator=llm, session=session)
    finally:
        await aclose(deps)


def _tenant(value: str) -> TenantId:
    return TenantId(UUID(value))


def _user(value: str) -> UserId:
    return UserId(UUID(value))


def _conn_id(value: str) -> ProviderConnectionId:
    return ProviderConnectionId(UUID(value))


def _resolve_key(kind: ProviderKind, key: str | None, key_stdin: bool) -> str:
    if key_stdin:
        key = sys.stdin.readline().strip()
    if not key:
        key = os.environ.get(_ENV_BY_KIND[kind])
    if not key:
        _console.print(
            f"[red]No API key provided.[/red] Pass --key, --key-stdin, or set "
            f"${_ENV_BY_KIND[kind]}."
        )
        raise typer.Exit(2)
    return key


@provider_app.command("add")
def add(
    kind: Annotated[ProviderKind, typer.Option("--kind", help="openrouter | nvidia_nim")],
    key: Annotated[str | None, typer.Option("--key", help="API key (never echoed)")] = None,
    key_stdin: Annotated[
        bool, typer.Option("--key-stdin", help="Read the API key from stdin")
    ] = False,
    name: Annotated[
        str | None, typer.Option("--name", help="Display name for the connection")
    ] = None,
    tenant: Annotated[
        str, typer.Option("--tenant", help="Tenant id (defaults to dev seed)")
    ] = DEV_TENANT_ID,
    user: Annotated[
        str, typer.Option("--user", help="User id (defaults to dev seed)")
    ] = DEV_USER_ID,
    base_url: Annotated[
        str | None, typer.Option("--base-url", help="Override the provider base URL")
    ] = None,
) -> None:
    """Validate an API key, store it in the vault, and cache the provider's models."""
    api_key = _resolve_key(kind, key, key_stdin)
    display_name = name or kind.value
    asyncio.run(_run_add(kind, api_key, display_name, tenant, user, base_url))


async def _run_add(
    kind: ProviderKind,
    api_key: str,
    display_name: str,
    tenant: str,
    user: str,
    base_url: str | None,
) -> None:
    try:
        async with _provider_service() as svc:
            conn = await svc.connect(
                tenant_id=_tenant(tenant),
                user_id=_user(user),
                kind=kind,
                api_key=api_key,
                display_name=display_name,
                base_url=base_url,
            )
    except VeraError as exc:
        _console.print(f"[red]provider add failed:[/red] {exc}")
        raise typer.Exit(1) from exc
    count = len(conn.available_models or [])
    _console.print(
        f"Connected [bold]{conn.display_name}[/bold] ({conn.kind.value}) "
        f"key={mask_key(api_key)} models={count}"
    )
    typer.echo(
        f"event=provider.connected kind={conn.kind.value} models={count} connection_id={conn.id}"
    )


@provider_app.command("list")
def list_(
    user: Annotated[
        str, typer.Option("--user", help="User id (defaults to dev seed)")
    ] = DEV_USER_ID,
) -> None:
    """Show connected providers with model counts and validation status."""
    asyncio.run(_run_list(user))


async def _run_list(user: str) -> None:
    async with _provider_service() as svc:
        conns = await svc.list_connections(user_id=_user(user))
    table = Table(title="Provider connections")
    for col in ("Name", "Kind", "Status", "Models", "Last validated", "Last error"):
        table.add_column(col)
    for c in conns:
        table.add_row(
            c.display_name,
            c.kind.value,
            c.status.value,
            str(len(c.available_models or [])),
            c.last_validated_at.isoformat() if c.last_validated_at else "-",
            c.last_error or "-",
        )
    _console.print(table)
    typer.echo(f"event=provider.listed count={len(conns)}")


@provider_app.command("validate")
def validate(
    connection_id: Annotated[str, typer.Argument(help="Provider connection id")],
    tenant: Annotated[
        str, typer.Option("--tenant", help="Tenant id (defaults to dev seed)")
    ] = DEV_TENANT_ID,
) -> None:
    """Re-run validation against the provider and update the stored status."""
    asyncio.run(_run_validate(connection_id, tenant))


async def _run_validate(connection_id: str, tenant: str) -> None:
    try:
        async with _provider_service() as svc:
            conn = await svc.revalidate(
                tenant_id=_tenant(tenant), connection_id=_conn_id(connection_id)
            )
    except VeraError as exc:
        _console.print(f"[red]provider validate failed:[/red] {exc}")
        raise typer.Exit(1) from exc
    _console.print(f"{conn.display_name}: [bold]{conn.status.value}[/bold]")
    typer.echo(f"event=provider.revalidated status={conn.status.value} connection_id={conn.id}")


@provider_app.command("rm")
def rm(
    connection_id: Annotated[str, typer.Argument(help="Provider connection id")],
    tenant: Annotated[
        str, typer.Option("--tenant", help="Tenant id (defaults to dev seed)")
    ] = DEV_TENANT_ID,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip the confirmation prompt")] = False,
) -> None:
    """Remove a provider connection and delete its Vault secret."""
    if not yes:
        typer.confirm(f"Remove provider connection {connection_id}?", abort=True)
    asyncio.run(_run_rm(connection_id, tenant))


async def _run_rm(connection_id: str, tenant: str) -> None:
    try:
        async with _provider_service() as svc:
            await svc.disconnect(tenant_id=_tenant(tenant), connection_id=_conn_id(connection_id))
    except VeraError as exc:
        _console.print(f"[red]provider rm failed:[/red] {exc}")
        raise typer.Exit(1) from exc
    typer.echo(f"event=provider.disconnected connection_id={connection_id}")


__all__ = ["provider_app"]
