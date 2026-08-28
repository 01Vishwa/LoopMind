"""``vera db`` — thin wrappers over the Supabase CLI migration commands."""

from __future__ import annotations

import shutil
import subprocess

import typer
from rich.console import Console

db_app = typer.Typer(no_args_is_help=True, help="Database migration commands (Supabase CLI).")
_console = Console(width=160)


def _require_supabase() -> None:
    if shutil.which("supabase") is None:
        _console.print(
            "[red]supabase CLI not found on PATH.[/red] Install it: "
            "https://supabase.com/docs/guides/cli"
        )
        raise typer.Exit(1)


@db_app.command("migrate")
def migrate() -> None:
    """Apply pending migrations via ``supabase db push``."""
    _require_supabase()
    proc = subprocess.run(["supabase", "db", "push"], check=False)
    raise typer.Exit(proc.returncode)


@db_app.command("status")
def status() -> None:
    """Show local vs. remote migration state via ``supabase migration list``."""
    _require_supabase()
    proc = subprocess.run(["supabase", "migration", "list"], check=False)
    raise typer.Exit(proc.returncode)


__all__ = ["db_app"]
