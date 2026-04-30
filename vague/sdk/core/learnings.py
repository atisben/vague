"""Learnings file management."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from vague.models import LearningEntry


def _get_learnings_path(slug: str) -> Path:
    home = Path(os.environ.get("VAGUE_HOME", Path.home() / ".vague"))
    return home / "projects" / slug / "learnings.md"


def _read_entries(path: Path) -> list[dict]:
    """Read all learning entries from the frontmatter list."""
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
    """Write learning entries to the frontmatter file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    import frontmatter
    post = frontmatter.Post("", entries=entries)
    content = frontmatter.dumps(post)
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(path)


def append_learning(slug: str, entry: LearningEntry) -> None:
    """Append to learnings.md. Prune to 500 by evicting lowest-confidence entries."""
    path = _get_learnings_path(slug)
    entries = _read_entries(path)

    entry_dict = json.loads(entry.model_dump_json())
    entries.append(entry_dict)

    if len(entries) > 500:
        entries.sort(key=lambda e: e.get("confidence", 0), reverse=True)
        entries = entries[:500]

    _write_entries(path, entries)


def search_learnings(
    slug: str,
    type_filter: str | None = None,
    min_confidence: int = 0,
) -> list[LearningEntry]:
    """Read and filter learnings. Dedup by (key, type) — keep latest."""
    path = _get_learnings_path(slug)
    entries = _read_entries(path)

    # Dedup: keep latest by (key, type)
    seen: dict[tuple, dict] = {}
    for e in entries:
        k = (e.get("key", ""), e.get("type", ""))
        existing = seen.get(k)
        if existing is None:
            seen[k] = e
        else:
            try:
                if _parse_ts(e.get("ts")) > _parse_ts(existing.get("ts")):
                    seen[k] = e
            except Exception:
                seen[k] = e

    results = list(seen.values())

    if type_filter:
        results = [e for e in results if e.get("type") == type_filter]
    if min_confidence > 0:
        results = [e for e in results if e.get("confidence", 0) >= min_confidence]

    out = []
    for e in results:
        try:
            out.append(LearningEntry(**e))
        except Exception:
            pass
    return out


def get_top_learnings(slug: str, n: int = 3) -> list[LearningEntry]:
    """Returns top n by confidence if >5 entries, else all."""
    all_entries = search_learnings(slug)
    if len(all_entries) <= 5:
        return all_entries
    sorted_entries = sorted(all_entries, key=lambda e: e.confidence, reverse=True)
    return sorted_entries[:n]


def _parse_ts(ts: Any) -> datetime:
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return datetime.min.replace(tzinfo=timezone.utc)
