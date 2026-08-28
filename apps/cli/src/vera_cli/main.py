"""``vera`` CLI entrypoint — wires the command groups into one Typer app."""

from __future__ import annotations

import typer

from vera_cli.commands.db import db_app
from vera_cli.commands.dev import dev_app
from vera_cli.commands.doctor import doctor
from vera_cli.commands.provider import provider_app
from vera_cli.commands.run import run

app = typer.Typer(
    no_args_is_help=True,
    help="VERA — verifiable data-analysis platform CLI.",
)
app.add_typer(provider_app, name="provider")
app.add_typer(db_app, name="db")
app.add_typer(dev_app, name="dev")
app.command()(doctor)
app.command()(run)


__all__ = ["app"]
