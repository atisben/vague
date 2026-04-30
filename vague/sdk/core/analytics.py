"""Analytics file management."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from vague.models import AnalyticsEntry


def _get_analytics_path() -> Path:
    home = Path(os.environ.get("VAGUE_HOME", Path.home() / ".vague"))
    return home / "analytics" / "skill-usage.md"


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


def append_analytics(entry: AnalyticsEntry) -> None:
    """Append to ~/.vague/analytics/skill-usage.md."""
    path = _get_analytics_path()
    entries = _read_entries(path)
    entries.append(json.loads(entry.model_dump_json()))
    _write_entries(path, entries)


def get_analytics(window: str = "all") -> list[AnalyticsEntry]:
    """Filter by window (7d, 30d, all)."""
    path = _get_analytics_path()
    entries = _read_entries(path)

    if window == "7d":
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    elif window == "30d":
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    else:
        cutoff = None

    result = []
    for e in entries:
        try:
            entry = AnalyticsEntry(**e)
            if cutoff is None or entry.ts >= cutoff:
                result.append(entry)
        except Exception:
            pass
    return result
