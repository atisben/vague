"""Per-project metadata (project.md) under ~/.vague/projects/{slug}/."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

from vague.sdk.core.frontmatter import update_md
from vague.sdk.core.logging import get_logger


def get_vague_home() -> Path:
    return Path(os.environ.get("VAGUE_HOME", Path.home() / ".vague"))


def _get_project_meta_path(slug: str) -> Path:
    return get_vague_home() / "projects" / slug / "project.md"


def upsert_project_meta(slug: str, path: Path) -> None:
    """Record where a project's repo lives and when it was last active.

    Written as a side effect of `vague context --skill`; status reads it to run
    git checks across projects.
    """
    def updater(existing: dict) -> dict:
        existing["path"] = str(path)
        existing["last_seen"] = datetime.now(UTC).isoformat()
        return existing

    update_md(_get_project_meta_path(slug), updater)


def read_project_meta(slug: str) -> dict:
    """Return {path, last_seen} for slug, or {} if never recorded (pre-upgrade)."""
    meta_path = _get_project_meta_path(slug)
    if not meta_path.exists():
        return {}
    try:
        import frontmatter
        post = frontmatter.load(str(meta_path))
        return dict(post.metadata)
    except Exception as e:
        get_logger().warning("failed to read project meta %s: %s", meta_path, e)
        return {}


def list_project_slugs() -> list[str]:
    """All project slugs with state under ~/.vague/projects/."""
    projects_dir = get_vague_home() / "projects"
    if not projects_dir.exists():
        return []
    return sorted(d.name for d in projects_dir.iterdir() if d.is_dir())
