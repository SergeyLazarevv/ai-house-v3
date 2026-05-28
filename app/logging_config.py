from __future__ import annotations

import logging
import os


def configure_logging() -> None:
    """Однократная настройка корневого логирования."""
    if logging.root.handlers:
        return
    level_name = (os.getenv("LOG_LEVEL") or "INFO").strip().upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
