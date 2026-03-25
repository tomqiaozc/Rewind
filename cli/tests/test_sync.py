"""Tests for sync command."""
from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from pathlib import Path

from typer.testing import CliRunner

from src.main import app

runner = CliRunner()


def test_sync_requires_auth(tmp_path: Path) -> None:
    """Sync should fail if not authenticated."""
    with patch("src.commands.sync._get_config") as mock_cfg:
        mock_cfg.return_value = MagicMock(is_authenticated=False)
        result = runner.invoke(app, ["sync"])
        assert result.exit_code != 0
        assert "Not authenticated" in result.output or "login" in result.output.lower()


def test_sync_no_sessions_found(tmp_path: Path) -> None:
    """Sync with no discoverable sessions should report nothing to sync."""
    with patch("src.commands.sync._get_config") as mock_cfg, \
         patch("src.commands.sync._get_parsers") as mock_parsers:
        cfg = MagicMock(
            is_authenticated=True,
            api_url="https://api.example.com",
            api_key="rw_test",
            config_dir=tmp_path,
        )
        mock_cfg.return_value = cfg
        mock_parsers.return_value = []
        result = runner.invoke(app, ["sync"])
        # Should succeed with "nothing to sync" message
        assert result.exit_code == 0


def test_sync_help() -> None:
    result = runner.invoke(app, ["sync", "--help"])
    assert result.exit_code == 0
    assert "Discover" in result.output or "sync" in result.output.lower()
