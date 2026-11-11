"""Frontmatter read/write for config.md and SKILL.md."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

import frontmatter


class FrontmatterError(Exception):
    pass


def _atomic_write(path: Path, content: str) -> None:
    """Write via a per-process temp file and rename, so a reader never sees a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f".{os.getpid()}.tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(path)


def _load(path: Path) -> frontmatter.Post:
    try:
        return frontmatter.load(str(path))
    except Exception as e:
        raise FrontmatterError(f"Failed to parse frontmatter in {path}: {e}") from e


def read_md(path: Path) -> dict:
    """Read frontmatter from a .md file. Returns {} if file doesn't exist."""
    if not path.exists():
        return {}
    return dict(_load(path).metadata)


def write_md(path: Path, data: dict, body: str = "") -> None:
    """Write frontmatter + body atomically. Creates parent dirs."""
    _atomic_write(path, frontmatter.dumps(frontmatter.Post(body, **data)))


def update_md(path: Path, updater: Callable[[dict], dict]) -> None:
    """Read-modify-write the frontmatter, keeping the body."""
    post = _load(path) if path.exists() else frontmatter.Post("")
    _atomic_write(path, frontmatter.dumps(frontmatter.Post(post.content, **updater(dict(post.metadata)))))
