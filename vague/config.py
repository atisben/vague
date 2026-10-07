"""Configuration for vague — where state lives and which Claude profiles to sync.

Lookup order for every setting: real environment variable first, then
``$VAGUE_HOME/config.env``. The env var wins so a one-off run can override the
persisted config without editing it.
"""

from __future__ import annotations

import os
from pathlib import Path

CONFIG_FILENAME = "config.env"
CLAUDE_DIRS_KEY = "VAGUE_CLAUDE_DIRS"
PATH_SEPARATOR = ":"


def vague_home() -> Path:
    """Return the vague state directory ($VAGUE_HOME, or ~/.vague)."""
    return Path(os.environ.get("VAGUE_HOME", "~/.vague")).expanduser()


def claude_d_dir() -> Path:
    """Return the directory holding the user's CLAUDE.md source fragments."""
    return vague_home() / "claude.d"


def load_config() -> dict[str, str]:
    """Parse $VAGUE_HOME/config.env into a dict. Missing file yields {}."""
    config_file = vague_home() / CONFIG_FILENAME
    if not config_file.is_file():
        return {}

    try:
        raw = config_file.read_text()
    except OSError:
        return {}

    config: dict[str, str] = {}
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        config[key.strip()] = value.strip().strip("\"'")
    return config


def _setting(key: str) -> str | None:
    """Read a setting from the environment, falling back to the config file."""
    return os.environ.get(key) or load_config().get(key)


def claude_dirs() -> list[Path]:
    """Return the Claude profile directories to sync, in declared order.

    Falls back to CLAUDE_CONFIG_DIR when VAGUE_CLAUDE_DIRS is unset, so a
    single-profile setup needs no vague config at all. An empty list means
    "nothing configured" — callers fall back to their own defaults.
    """
    raw = _setting(CLAUDE_DIRS_KEY) or os.environ.get("CLAUDE_CONFIG_DIR")
    if not raw:
        return []

    dirs: list[Path] = []
    for segment in raw.split(PATH_SEPARATOR):
        candidate = segment.strip()
        if not candidate:
            continue
        resolved = Path(candidate).expanduser()
        if resolved not in dirs:
            dirs.append(resolved)
    return dirs


def profile_name_for(directory: Path) -> str:
    """Derive a readable profile name from a Claude config directory.

    ``~/.claude-work`` becomes ``work``, ``~/.claude`` becomes ``default``.
    The name selects the per-profile overlay in ``claude.d/<name>.md``.
    """
    name = directory.name.lstrip(".")
    if name == "claude":
        return "default"
    for prefix in ("claude-", "claude_"):
        if name.startswith(prefix):
            return name[len(prefix) :]
    return name
