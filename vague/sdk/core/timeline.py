"""Timeline file management."""

from __future__ import annotations

import json
import os
from pathlib import Path

from vague.models import TimelineEntry


def _get_timeline_path(slug: str) -> Path:
    home = Path(os.environ.get("VAGUE_HOME", Path.home() / ".vague"))
    return home / "projects" / slug / "timeline.md"


def _read_entries(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        import frontmatter
        post = frontmatter.load(str(path))
        entries = post.metadata.get("entries", [])
        return entries if isinstance(entries, list) else []
    except Exception:
        return []


def _write_entries(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    import frontmatter
    post = frontmatter.Post("", entries=entries)
    content = frontmatter.dumps(post)
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(path)


def append_timeline(slug: str, entry: TimelineEntry) -> None:
    """Append to timeline.md for slug."""
    path = _get_timeline_path(slug)
    entries = _read_entries(path)
    entries.append(json.loads(entry.model_dump_json()))
    _write_entries(path, entries)
