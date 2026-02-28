from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from backend.paths import log_path


def build_logger(path: Path | None = None) -> logging.Logger:
    logger = logging.getLogger("limpiaraxess")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    destination = path or log_path()
    destination.parent.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        destination,
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.propagate = False
    return logger
