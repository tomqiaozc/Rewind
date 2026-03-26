"""Tests for CLI version command."""
from __future__ import annotations

from typer.testing import CliRunner

from src.main import app

runner = CliRunner()


def test_version_flag() -> None:
    """Version flag should output version string."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_no_args_shows_help() -> None:
    """No arguments should show help text."""
    result = runner.invoke(app, [])
    assert result.exit_code in (0, 2)
    assert "Rewind" in result.output or "Usage" in result.output
