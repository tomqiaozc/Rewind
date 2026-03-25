"""Sync command — discover, parse, upload sessions."""
from __future__ import annotations

import typer


def sync() -> None:
    """Discover local AI sessions, parse, and upload to Rewind."""
    typer.echo("Sync not yet implemented")
    raise typer.Exit(1)
