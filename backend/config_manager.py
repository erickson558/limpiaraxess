from __future__ import annotations

import json
import re
import threading
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.paths import config_path
from backend.version import VERSION

GEOMETRY_PATTERN = re.compile(r"^\d{3,5}x\d{3,5}[+-]\d{1,5}[+-]\d{1,5}$")
DEFAULT_GEOMETRY = "1180x760+120+80"


@dataclass
class AppConfig:
    version: str = VERSION
    target_path: str = ""
    auto_start: bool = False
    auto_close_enabled: bool = False
    auto_close_seconds: int = 60
    window_geometry: str = DEFAULT_GEOMETRY
    password_required: bool = False
    password_hash: str = ""
    password_salt: str = ""
    ui: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "target_path": self.target_path,
            "auto_start": self.auto_start,
            "auto_close_enabled": self.auto_close_enabled,
            "auto_close_seconds": self.auto_close_seconds,
            "window_geometry": self.window_geometry,
            "password_required": self.password_required,
            "password_hash": self.password_hash,
            "password_salt": self.password_salt,
            "ui": deepcopy(self.ui),
        }


class ConfigManager:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or config_path()
        self._lock = threading.Lock()
        self._config = AppConfig()
        self.load()

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> AppConfig:
        with self._lock:
            loaded: dict[str, Any] = {}
            if self._path.exists():
                loaded = self._safe_load_json(self._path)

            cfg = AppConfig()
            cfg.version = str(loaded.get("version", VERSION))
            cfg.target_path = str(loaded.get("target_path", ""))
            cfg.auto_start = bool(loaded.get("auto_start", False))
            cfg.auto_close_enabled = bool(loaded.get("auto_close_enabled", False))
            cfg.auto_close_seconds = self._clamp_seconds(loaded.get("auto_close_seconds", 60))
            cfg.window_geometry = self._sanitize_geometry(loaded.get("window_geometry", DEFAULT_GEOMETRY))
            cfg.password_required = bool(loaded.get("password_required", False))
            cfg.password_hash = str(loaded.get("password_hash", ""))
            cfg.password_salt = str(loaded.get("password_salt", ""))
            cfg.ui = loaded.get("ui", {}) if isinstance(loaded.get("ui", {}), dict) else {}
            cfg.version = VERSION

            self._config = cfg
            self._atomic_write(cfg.to_dict())
            return deepcopy(cfg)

    def get(self) -> AppConfig:
        with self._lock:
            return deepcopy(self._config)

    def update(self, **kwargs: Any) -> AppConfig:
        with self._lock:
            for key, value in kwargs.items():
                if not hasattr(self._config, key):
                    continue
                if key == "auto_close_seconds":
                    value = self._clamp_seconds(value)
                if key == "window_geometry":
                    value = self._sanitize_geometry(value)
                setattr(self._config, key, value)

            self._config.version = VERSION
            self._atomic_write(self._config.to_dict())
            return deepcopy(self._config)

    def _safe_load_json(self, path: Path) -> dict[str, Any]:
        max_size = 1_000_000
        if path.stat().st_size > max_size:
            return {}

        try:
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
                return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _atomic_write(self, data: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self._path.with_suffix(".json.tmp")
        with temp_path.open("w", encoding="utf-8", newline="\n") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        temp_path.replace(self._path)

    @staticmethod
    def _clamp_seconds(value: Any) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = 60
        return max(5, min(parsed, 86_400))

    @staticmethod
    def _sanitize_geometry(value: Any) -> str:
        text = str(value)
        if GEOMETRY_PATTERN.match(text):
            return text
        return DEFAULT_GEOMETRY
