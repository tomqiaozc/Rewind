"""Login command — authenticate with Rewind API."""
from __future__ import annotations

import typer
from rich.console import Console

from src.config.manager import ConfigManager

console = Console()


def login(
    api_url: str = typer.Option(
        "http://localhost:8000",
        "--api-url",
        help="Rewind API base URL",
    ),
) -> None:
    """Authenticate with the Rewind API.

    For now, prompts for an API key. Browser OAuth will be added in a future release.
    """
    console.print("[bold]Rewind Login[/bold]")
    console.print(f"API URL: {api_url}")
    console.print()
    console.print("Go to your Rewind dashboard → Settings → API Keys to generate a key.")
    console.print()

    api_key = typer.prompt("Paste your API key (rw_...)")

    if not api_key.startswith("rw_"):
        console.print("[red]Invalid API key. Keys must start with 'rw_'.[/red]")
        raise typer.Exit(1)

    config = ConfigManager()
    config.api_url = api_url
    config.api_key = api_key
    config.save()

    console.print("[green]Successfully authenticated![/green]")
    console.print(f"Config saved to: {config.config_dir / 'config.json'}")
