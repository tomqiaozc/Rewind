"""Status command — show sync state."""
from __future__ import annotations

from rich.console import Console
from rich.table import Table

from src.config.cursors import CursorStore
from src.config.manager import ConfigManager

console = Console()


def status() -> None:
    """Show current sync state and session counts."""
    config = ConfigManager()

    table = Table(title="Rewind CLI Status")
    table.add_column("Setting", style="cyan")
    table.add_column("Value")

    auth_value = "[green]Yes[/green]" if config.is_authenticated else "[red]No[/red]"
    table.add_row("Authenticated", auth_value)
    table.add_row("API URL", config.api_url or "[dim]not set[/dim]")
    table.add_row("Device ID", config.device_id[:8] + "...")
    table.add_row("Config Dir", str(config.config_dir))

    console.print(table)

    if config.is_authenticated:
        cursor_store = CursorStore(config_dir=config.config_dir)
        keys = cursor_store.all_keys()
        if keys:
            cursor_table = Table(title="Tracked Sources")
            cursor_table.add_column("Source", style="cyan")
            cursor_table.add_column("Cursor Key")
            for key in keys:
                source = key.split(":")[0] if ":" in key else "unknown"
                cursor_table.add_row(source, key)
            console.print(cursor_table)
        else:
            console.print("\n[dim]No sync history yet. Run 'rewind sync' to start.[/dim]")
