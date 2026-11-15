"""Frontmatter reader for SKILL.md and agent files."""

from __future__ import annotations

from pathlib import Path

import frontmatter


class FrontmatterError(Exception):
    pass


def read_md(path: Path) -> dict:
    """Read frontmatter from a .md file. Returns {} if file doesn't exist."""
    if not path.exists():
        return {}
    try:
        return dict(frontmatter.load(str(path)).metadata)
    except Exception as e:
        raise FrontmatterError(f"Failed to parse frontmatter in {path}: {e}") from e
