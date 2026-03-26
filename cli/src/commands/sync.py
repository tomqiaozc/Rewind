"""Sync command — discover, parse, upload sessions."""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Optional

import httpx
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.config.cursors import CursorStore
from src.config.manager import ConfigManager
from src.parsers.claude import ClaudeParser
from src.parsers.gemini import GeminiParser
from src.parsers.opencode import OpenCodeParser
from src.upload.engine import UploadEngine

if TYPE_CHECKING:
    from src.parsers.base import BaseParser, ParseResult

logger = logging.getLogger(__name__)
console = Console()


def _get_config() -> ConfigManager:
    return ConfigManager()


def _get_parsers() -> list[BaseParser]:
    parsers: list[BaseParser] = []
    parsers.append(ClaudeParser())
    parsers.append(OpenCodeParser())
    parsers.append(GeminiParser())
    return parsers


def sync(
    source: Optional[str] = typer.Option(
        None, "--source", "-s",
        help="Filter by source (claude, opencode, gemini)",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Show what would be synced without uploading",
    ),
) -> None:
    """Discover local AI sessions, parse, and upload to Rewind."""
    config = _get_config()
    if not config.is_authenticated:
        console.print(
            "[red]Not authenticated. Run 'rewind login' first.[/red]",
        )
        raise typer.Exit(1)

    cursor_store = CursorStore(config_dir=config.config_dir)
    parsers = _get_parsers()

    if source:
        parsers = [p for p in parsers if p.source_name == source]
        if not parsers:
            console.print(f"[red]Unknown source: {source}[/red]")
            raise typer.Exit(1)

    # Discover and parse
    all_results: list[ParseResult] = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for parser in parsers:
            task = progress.add_task(
                f"Parsing {parser.source_name}...", total=None,
            )
            try:
                results = parser.parse_all()
                all_results.extend(results)
                progress.update(
                    task,
                    description=(
                        f"[green]{parser.source_name}:"
                        f" {len(results)} sessions[/green]"
                    ),
                )
            except Exception as exc:
                progress.update(
                    task,
                    description=(
                        f"[red]{parser.source_name}:"
                        f" error — {exc}[/red]"
                    ),
                )
                logger.exception("Parser %s failed", parser.source_name)

    if not all_results:
        console.print("Nothing to sync.")
        raise typer.Exit(0)

    console.print(f"Found {len(all_results)} session(s) to sync.")

    if dry_run:
        for r in all_results:
            console.print(
                f"  [{r.canonical.source}]"
                f" {r.canonical.session_key}"
                f" — {r.canonical.total_messages} messages",
            )
        raise typer.Exit(0)

    # Upload
    asyncio.run(_upload_all(config, cursor_store, all_results))


async def _upload_all(
    config: ConfigManager,
    cursor_store: CursorStore,
    results: list[ParseResult],
) -> None:
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {config.api_key}"},
        timeout=60.0,
    ) as client:
        engine = UploadEngine(
            client=client, api_url=config.api_url or "",
        )

        success_count = 0
        fail_count = 0

        for r in results:
            metadata = r.canonical.model_dump(mode="json")
            metadata.pop("messages", None)
            canonical_data = r.canonical.model_dump(mode="json")
            raw_data = r.raw.model_dump(mode="json")
            raw_hash = r.canonical.raw_hash

            ok = await engine.upload_session(
                metadata, canonical_data, raw_data, raw_hash,
            )
            if ok:
                if r.cursor:
                    cursor_store.set(r.cursor_key, r.cursor)
                success_count += 1
            else:
                cursor_store.rollback(r.cursor_key)
                fail_count += 1

        if success_count > 0:
            cursor_store.save()

        console.print(
            f"[green]Synced: {success_count}[/green],"
            f" [red]Failed: {fail_count}[/red]",
        )
