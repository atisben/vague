"""Cross-project status collection for `vague status`."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

from vague.sdk.core.logging import get_logger
from vague.sdk.core.projects import get_vague_home, list_project_slugs, read_project_meta

GIT_TIMEOUT_S = 2

# Timeline skill names that count as "shipped" for in-flight design detection.
SHIP_SKILLS = {"ship", "dev-ship"}


def collect_status() -> list[dict]:
    """One row per project, most recently seen first.

    Row: {slug, path, path_state, branch, dirty, last_seen, last_event,
          inflight_designs, learnings}
    path_state: live | stale | unknown
    """
    rows = [_project_row(slug) for slug in list_project_slugs()]
    rows.sort(key=lambda r: r["last_seen"] or "", reverse=True)
    return rows


def _project_row(slug: str) -> dict:
    project_dir = get_vague_home() / "projects" / slug
    meta = read_project_meta(slug)
    path = meta.get("path")
    # YAML may resolve an unquoted timestamp to datetime; rows expect strings
    last_seen = meta.get("last_seen")
    if last_seen is not None:
        last_seen = str(last_seen)

    row: dict = {
        "slug": slug,
        "path": path,
        "path_state": "unknown",
        "branch": None,
        "dirty": None,
        "last_seen": last_seen,
        "last_event": _last_timeline_event(project_dir),
        "inflight_designs": _count_inflight_designs(project_dir),
        "learnings": _count_entries(project_dir / "learnings.md"),
    }

    if path:
        repo = Path(path)
        if repo.is_dir():
            row["path_state"] = "live"
            row["branch"] = _git(repo, "branch", "--show-current")
            porcelain = _git(repo, "status", "--porcelain")
            row["dirty"] = bool(porcelain) if porcelain is not None else None
        else:
            row["path_state"] = "stale"
    return row


def _git(repo: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, timeout=GIT_TIMEOUT_S,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        get_logger().debug("status: git %s failed for %s: %s", args, repo, e)
    return None


def _read_frontmatter_entries(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        import frontmatter
        post = frontmatter.load(str(path))
        entries = post.metadata.get("entries", [])
        return entries if isinstance(entries, list) else []
    except Exception as e:
        get_logger().warning("status: failed to read %s: %s", path, e)
        return []


def _count_entries(path: Path) -> int:
    return len(_read_frontmatter_entries(path))


def _last_timeline_event(project_dir: Path) -> dict | None:
    entries = _read_frontmatter_entries(project_dir / "timeline.md")
    if not entries:
        return None
    last = entries[-1]
    return {"skill": last.get("skill"), "event": last.get("event"), "ts": str(last.get("ts", ""))}


def _last_ship_ts(project_dir: Path) -> datetime | None:
    entries = _read_frontmatter_entries(project_dir / "timeline.md")
    ship_ts = None
    for e in entries:
        if e.get("skill") in SHIP_SKILLS and e.get("event") == "completed":
            try:
                ship_ts = datetime.fromisoformat(str(e["ts"]))
            except (KeyError, ValueError):
                continue
    if ship_ts is not None and ship_ts.tzinfo is None:
        ship_ts = ship_ts.replace(tzinfo=UTC)
    return ship_ts


def _count_inflight_designs(project_dir: Path) -> int:
    """Design docs newer than the last ship event — plans not yet implemented."""
    designs_dir = project_dir / "designs"
    if not designs_dir.is_dir():
        return 0
    ship_ts = _last_ship_ts(project_dir)
    count = 0
    for doc in designs_dir.glob("*.md"):
        if ship_ts is None:
            count += 1
            continue
        doc_ts = datetime.fromtimestamp(doc.stat().st_mtime, tz=UTC)
        if doc_ts > ship_ts:
            count += 1
    return count
