"""Shared channels.txt file management."""

import os
from pathlib import Path
from typing import List
from loguru import logger

CHANNELS_FILE = Path("channels.txt")


def load_channels() -> List[str]:
    """Read channel usernames from channels.txt (ignores comments and blanks)."""
    if not CHANNELS_FILE.exists():
        CHANNELS_FILE.write_text("# Monitored Telegram Channels\n# One per line, with or without @\n")
        return []

    channels = []
    for line in CHANNELS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            if not line.startswith("@"):
                line = "@" + line
            channels.append(line)

    logger.info(f"Loaded {len(channels)} channels from {CHANNELS_FILE}")
    return channels


def save_channels(channels: List[str]) -> None:
    """Overwrite channels.txt with the given list."""
    with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
        f.write("# Monitored Telegram Channels\n# One per line, with or without @\n\n")
        for ch in channels:
            f.write(f"{ch}\n")
    logger.info(f"Saved {len(channels)} channels to {CHANNELS_FILE}")


def get_file_mtime() -> float:
    """Return modification time of channels.txt (0.0 if missing)."""
    return os.path.getmtime(CHANNELS_FILE) if CHANNELS_FILE.exists() else 0.0
