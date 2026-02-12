"""Logging configuration using Loguru."""

import sys
from pathlib import Path
from loguru import logger


def setup_logger(log_level: str = "INFO", log_file: str = "logs/app.log") -> None:
    """Configure application-wide logging with console + file output."""
    logger.remove()
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    # Console: colored, concise
    logger.add(
        sys.stdout,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan> | "
            "<level>{message}</level>"
        ),
        level=log_level,
        colorize=True,
    )

    # File: detailed with rotation
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        enqueue=True,
    )

    # Separate error log
    logger.add(
        str(Path(log_file).parent / "error.log"),
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}\n{exception}",
        level="ERROR",
        rotation="5 MB",
        retention="30 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
        enqueue=True,
    )
