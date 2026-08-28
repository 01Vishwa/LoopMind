"""``vera dev`` — local development helpers (fixture seeding)."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from sqlalchemy import text
from vera_db import DbConfig, build_direct_engine

from vera_cli.constants import DEV_TENANT_ID, DEV_USER_ID

dev_app = typer.Typer(no_args_is_help=True, help="Local development helpers.")
_console = Console(width=160)

_SEED_TENANT = text(
    "insert into public.tenants (id, name) values (:id, 'VERA Dev') on conflict (id) do nothing"
)
_SEED_USER = text(
    "insert into public.users (id, tenant_id, email, full_name) "
    "values (:id, :tenant_id, 'dev@vera.local', 'Dev User') "
    "on conflict (id) do nothing"
)


async def _run_seed() -> None:
    cfg = DbConfig.from_env()
    engine = build_direct_engine(cfg.direct_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(_SEED_TENANT, {"id": DEV_TENANT_ID})
            await conn.execute(_SEED_USER, {"id": DEV_USER_ID, "tenant_id": DEV_TENANT_ID})
    finally:
        await engine.dispose()


@dev_app.command("seed")
def seed() -> None:
    """Upsert the fixed demo tenant + user and print their ids."""
    asyncio.run(_run_seed())
    _console.print(f"Seeded tenant [bold]{DEV_TENANT_ID}[/bold] user [bold]{DEV_USER_ID}[/bold]")
    typer.echo(f"event=dev.seeded tenant={DEV_TENANT_ID} user={DEV_USER_ID}")


__all__ = ["dev_app"]
