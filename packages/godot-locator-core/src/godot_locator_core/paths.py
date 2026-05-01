"""Cross-platform user-data directory resolution.

- Linux:   `$XDG_DATA_HOME/godot-locator` or `~/.local/share/godot-locator`
- macOS:   `~/Library/Application Support/godot-locator`
- Windows: `%LOCALAPPDATA%\\godot-locator`

`GODOT_LOCATOR_DATA_HOME` overrides on every platform — used by tests.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "godot-locator"
ENV_DATA_HOME = "GODOT_LOCATOR_DATA_HOME"


def user_data_dir() -> Path:
    override = os.environ.get(ENV_DATA_HOME)
    if override:
        return Path(override)

    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / APP_NAME
        return Path.home() / "AppData" / "Local" / APP_NAME

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME

    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / APP_NAME
    return Path.home() / ".local" / "share" / APP_NAME


def sessions_dir() -> Path:
    return user_data_dir() / "sessions"
