"""Analytics file management."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from vague.models import AnalyticsEntry
from vague.sdk.core.frontmatter import file_lock
from vague.sdk.core.logging import get_logger


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
    except Exception as e:
        get_logger().warning("failed to read entries from %s: %s", path, e)
        return []


def _write_entries(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    import frontmatter
    post = frontmatter.Post("", entries=entries)
    content = frontmatter.dumps(post)
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(path)


MAX_ENTRIES = 1000


def append_analytics(entry: AnalyticsEntry) -> None:
    """Append to ~/.vague/analytics/skill-usage.md. Capped: oldest evicted past MAX_ENTRIES."""
    path = _get_analytics_path()
    entry_dict = json.loads(entry.model_dump_json())
    with file_lock(path):
        entries = _read_entries(path)
        entries.append(entry_dict)
        if len(entries) > MAX_ENTRIES:
            entries = entries[-MAX_ENTRIES:]
        _write_entries(path, entries)


def record_skill_start(skill: str, slug: str, branch: str) -> None:
    """Mechanical usage capture: one entry per skill preamble invocation."""
    entry = AnalyticsEntry(
        skill=skill,
        ts=datetime.now(UTC),
        repo=slug,
        branch=branch,
        event="start",
    )
    append_analytics(entry)


def get_analytics(window: str = "all") -> list[AnalyticsEntry]:
    """Filter by window (7d, 30d, all)."""
    path = _get_analytics_path()
    entries = _read_entries(path)

    if window == "7d":
        cutoff = datetime.now(UTC) - timedelta(days=7)
    elif window == "30d":
        cutoff = datetime.now(UTC) - timedelta(days=30)
    else:
        cutoff = None

    result = []
    for e in entries:
        try:
            entry = AnalyticsEntry(**e)
            if cutoff is None or entry.ts >= cutoff:
                result.append(entry)
        except Exception as e:
            get_logger().debug("get_analytics: skipping malformed entry: %s", e)
    return result
