"""Login command — authenticate with Rewind API."""
from __future__ import annotations

import typer


def login() -> None:
    """Authenticate with the Rewind API via browser OAuth."""
    typer.echo("Login not yet implemented")
    raise typer.Exit(1)
