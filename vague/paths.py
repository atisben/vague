"""Where vague keeps its state, and how a state file is replaced safely."""

from __future__ import annotations

import os
from pathlib import Path


def vague_home() -> Path:
    """$VAGUE_HOME, or ~/.vague when it is unset or empty."""
    return Path(os.environ.get("VAGUE_HOME") or "~/.vague").expanduser()


def atomic_write(path: Path, text: str) -> None:
    """Write via a per-process temp file and rename, so a reader never sees a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
