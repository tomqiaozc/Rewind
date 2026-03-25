"""Config manager — handles ~/.config/rewind/config.json."""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Optional

import platformdirs


def _default_config_dir() -> Path:
    return Path(platformdirs.user_config_dir("rewind", ensure_exists=True))


class ConfigManager:
    """Manages CLI configuration (API URL, API key, device ID)."""

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        self._config_dir = config_dir or _default_config_dir()
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._config_file = self._config_dir / "config.json"

        self.api_url: Optional[str] = None
        self.api_key: Optional[str] = None
        self.device_id: str = str(uuid.uuid4())

        self._load()

    def _load(self) -> None:
        if self._config_file.exists():
            data = json.loads(self._config_file.read_text())
            self.api_url = data.get("api_url")
            self.api_key = data.get("api_key")
            self.device_id = data.get("device_id", self.device_id)

    def save(self) -> None:
        data = {
            "api_url": self.api_url,
            "api_key": self.api_key,
            "device_id": self.device_id,
        }
        self._config_file.write_text(json.dumps(data, indent=2) + "\n")

    @property
    def is_authenticated(self) -> bool:
        return bool(self.api_url and self.api_key)

    @property
    def config_dir(self) -> Path:
        return self._config_dir
