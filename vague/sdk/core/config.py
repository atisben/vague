"""Config file management."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from vague.models import ConfigModel
from vague.sdk.core.frontmatter import read_md, update_md, FrontmatterError

VAGUE_HOME: Path = Path(os.environ.get("VAGUE_HOME", Path.home() / ".vague"))


def _get_home() -> Path:
    """Get VAGUE_HOME, respecting env override (for tests)."""
    return Path(os.environ.get("VAGUE_HOME", Path.home() / ".vague"))


def get_config() -> ConfigModel:
    """Read ~/.vague/config.md. On error → return defaults + warn to stderr."""
    home = _get_home()
    config_path = home / "config.md"
    try:
        data = read_md(config_path)
        return ConfigModel(**{k: v for k, v in data.items() if k in ConfigModel.model_fields})
    except FrontmatterError as e:
        print(f"Warning: could not parse config.md: {e}", file=sys.stderr)
        return ConfigModel()
    except Exception as e:
        print(f"Warning: could not read config: {e}", file=sys.stderr)
        return ConfigModel()


def set_config_key(key: str, value: Any) -> None:
    """Atomic update of single key in config.md."""
    home = _get_home()
    config_path = home / "config.md"

    def updater(data: dict) -> dict:
        data[key] = value
        return data

    update_md(config_path, updater)
