"""Tests for config manager."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from src.config.manager import ConfigManager

if TYPE_CHECKING:
    from pathlib import Path


def test_default_config(tmp_path: Path) -> None:
    mgr = ConfigManager(config_dir=tmp_path)
    assert mgr.api_url is None
    assert mgr.api_key is None
    assert mgr.device_id is not None  # auto-generated UUID


def test_save_and_load(tmp_path: Path) -> None:
    mgr = ConfigManager(config_dir=tmp_path)
    mgr.api_url = "https://api.example.com"
    mgr.api_key = "rw_test123"
    mgr.save()

    mgr2 = ConfigManager(config_dir=tmp_path)
    assert mgr2.api_url == "https://api.example.com"
    assert mgr2.api_key == "rw_test123"
    assert mgr2.device_id == mgr.device_id


def test_config_file_created(tmp_path: Path) -> None:
    mgr = ConfigManager(config_dir=tmp_path)
    mgr.api_url = "https://api.example.com"
    mgr.save()
    config_file = tmp_path / "config.json"
    assert config_file.exists()
    data = json.loads(config_file.read_text())
    assert data["api_url"] == "https://api.example.com"


def test_is_authenticated(tmp_path: Path) -> None:
    mgr = ConfigManager(config_dir=tmp_path)
    assert not mgr.is_authenticated
    mgr.api_url = "https://api.example.com"
    mgr.api_key = "rw_test123"
    assert mgr.is_authenticated
