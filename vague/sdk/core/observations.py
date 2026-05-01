"""Observations file management for the /meta skill."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from vague.models import ObservationEntry


def _get_observations_path(slug: str) -> Path:
    home = Path(os.environ.get("VAGUE_HOME", Path.home() / ".vague"))
    return home / "projects" / slug / "observations.md"


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


def _next_id(entries: list[dict]) -> int:
    if not entries:
        return 1
    max_id = max(e.get("id", 0) for e in entries)
    return max_id + 1


def append_observation(slug: str, entry: ObservationEntry) -> None:
    path = _get_observations_path(slug)
    entries = _read_entries(path)
    entry_dict = json.loads(entry.model_dump_json())
    entries.append(entry_dict)
    _write_entries(path, entries)


def list_observations(
    slug: str,
    status_filter: str | None = None,
) -> list[ObservationEntry]:
    path = _get_observations_path(slug)
    entries = _read_entries(path)

    if status_filter:
        entries = [e for e in entries if e.get("status") == status_filter]

    out = []
    for e in entries:
        try:
            out.append(ObservationEntry(**e))
        except Exception:
            pass
    return out


def update_observation_status(slug: str, obs_id: int, new_status: str) -> bool:
    """Update an observation's status. Returns True if found and updated."""
    path = _get_observations_path(slug)
    entries = _read_entries(path)

    found = False
    for e in entries:
        if e.get("id") == obs_id:
            e["status"] = new_status
            found = True
            break

    if found:
        _write_entries(path, entries)
    return found


def next_observation_id(slug: str) -> int:
    path = _get_observations_path(slug)
    entries = _read_entries(path)
    return _next_id(entries)
