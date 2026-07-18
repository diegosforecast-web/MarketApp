from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)


def configure_logging() -> None:
    """
    Configure console and rotating-file logging once.

    Environment variables:
        LOG_LEVEL=INFO
        LOG_DIR=logs
        LOG_MAX_BYTES=10485760
        LOG_BACKUP_COUNT=5
    """
    root_logger = logging.getLogger()

    if getattr(root_logger, "_dimarket_configured", False):
        return

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    log_dir = Path(os.getenv("LOG_DIR", "logs"))
    log_dir.mkdir(parents=True, exist_ok=True)

    max_bytes = int(
        os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024))
    )
    backup_count = int(
        os.getenv("LOG_BACKUP_COUNT", "5")
    )

    formatter = logging.Formatter(LOG_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_dir / "dimarket.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    root_logger.handlers.clear()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Reduce noisy third-party logs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    root_logger._dimarket_configured = True
