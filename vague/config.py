"""Configuration for vague: one file, $VAGUE_HOME/config.env, of `KEY=value` lines.

It holds the Claude profiles to sync (`VAGUE_CLAUDE_DIRS`) and `telemetry` (`local` or `off`).
For the profiles, a real environment variable wins over the file, so a one-off run can
override the persisted config without editing it.
"""

from __future__ import annotations

import os
from pathlib import Path

from vague.models import ConfigModel
from vague.paths import atomic_write, vague_home

CONFIG_FILENAME = "config.env"
CLAUDE_DIRS_KEY = "VAGUE_CLAUDE_DIRS"
PATH_SEPARATOR = ":"


def config_path() -> Path:
    return vague_home() / CONFIG_FILENAME


def _parse_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key, _, value = stripped.partition("=")
    return key.strip(), value.strip().strip("\"'")


def load_config() -> dict[str, str]:
    """Every `KEY=value` in config.env. A missing or unreadable file yields {}. Never logs, never prints."""
    try:
        raw = config_path().read_text()
    except OSError:
        return {}
    return dict(parsed for line in raw.splitlines() if (parsed := _parse_line(line)))


def get_config() -> ConfigModel:
    """The typed settings, with defaults for every key the file leaves out."""
    # Imported here: the event log reads load_config to check telemetry.
    from vague.sdk.core.events import log_context_access

    log_context_access(kind="read", path=config_path())
    data = load_config()
    return ConfigModel(**{k: v for k, v in data.items() if k in ConfigModel.model_fields})


def set_config_key(key: str, value: str) -> None:
    """Set one key in config.env, keeping every other line, comments included."""
    from vague.sdk.core.events import log_context_access

    path = config_path()
    try:
        lines = path.read_text().splitlines()
    except OSError:
        lines = []
    entry = f"{key}={value}"
    replaced = [entry if (parsed := _parse_line(line)) and parsed[0] == key else line for line in lines]
    if entry not in replaced:
        replaced.append(entry)
    atomic_write(path=path, text="\n".join(replaced) + "\n")
    log_context_access(kind="write", path=path)


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
    The name becomes the runtime key suffix, as in ``claude:work``.
    """
    name = directory.name.lstrip(".")
    if name == "claude":
        return "default"
    for prefix in ("claude-", "claude_"):
        if name.startswith(prefix):
            return name[len(prefix) :]
    return name
