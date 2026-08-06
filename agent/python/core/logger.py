from __future__ import annotations

import logging
from pathlib import Path


def configure_logger(
    logs_directory: Path,
    logger_name: str = "printflow_agent",
) -> logging.Logger:
    logs_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(
        logs_directory / "printflow-agent.log",
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
