"""Status command — show sync state."""
from __future__ import annotations

import typer


def status() -> None:
    """Show current sync state and session counts."""
    typer.echo("Status not yet implemented")
    raise typer.Exit(1)
