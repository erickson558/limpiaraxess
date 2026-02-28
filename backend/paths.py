from __future__ import annotations

import sys
from pathlib import Path


def get_runtime_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def config_path() -> Path:
    return get_runtime_dir() / "config.json"


def log_path() -> Path:
    return get_runtime_dir() / "log.txt"
