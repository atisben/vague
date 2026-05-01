"""Cross-cutting principles file management for the /meta skill."""

from __future__ import annotations

import json
import os
from pathlib import Path

from vague.models import PrincipleEntry


def _get_principles_path(slug: str) -> Path:
    home = Path(os.environ.get("VAGUE_HOME", Path.home() / ".vague"))
    return home / "projects" / slug / "principles.md"


def _read_entries(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        import frontmatter

        post = frontmatter.load(str(path))
        entries = post.metadata.get("principles", [])
        return entries if isinstance(entries, list) else []
    except Exception:
        return []


def _write_entries(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    import frontmatter

    post = frontmatter.Post("", principles=entries)
    content = frontmatter.dumps(post)
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(path)


def _next_id(entries: list[dict]) -> int:
    if not entries:
        return 1
    max_id = max(e.get("id", 0) for e in entries)
    return max_id + 1


def append_principle(slug: str, entry: PrincipleEntry) -> None:
    path = _get_principles_path(slug)
    entries = _read_entries(path)
    entry_dict = json.loads(entry.model_dump_json())
    entries.append(entry_dict)
    _write_entries(path, entries)


def list_principles(
    slug: str,
    status_filter: str | None = "active",
) -> list[PrincipleEntry]:
    path = _get_principles_path(slug)
    entries = _read_entries(path)

    if status_filter:
        entries = [e for e in entries if e.get("status") == status_filter]

    out = []
    for e in entries:
        try:
            out.append(PrincipleEntry(**e))
        except Exception:
            pass
    return out


def update_principle_status(slug: str, principle_id: int, new_status: str) -> bool:
    """Update a principle's status. Returns True if found and updated."""
    path = _get_principles_path(slug)
    entries = _read_entries(path)

    found = False
    for e in entries:
        if e.get("id") == principle_id:
            e["status"] = new_status
            found = True
            break

    if found:
        _write_entries(path, entries)
    return found
