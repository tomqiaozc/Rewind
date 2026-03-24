"""Rewind CLI — entry point."""
from __future__ import annotations

import typer

app = typer.Typer(
    name="rewind",
    help="Rewind — sync and manage your AI coding sessions.",
    no_args_is_help=True,
)


@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(False, "--version", "-v", help="Show version"),
) -> None:
    """Rewind — sync and manage your AI coding sessions."""
    if version:
        typer.echo("rewind-cli 0.1.0")
        raise typer.Exit()


if __name__ == "__main__":
    app()
