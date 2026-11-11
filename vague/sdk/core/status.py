"""Cross-project status for `vague status`, derived from the events log and the memory ledger.

A project is any `repo` that appears in an event, or any ledger scope except `global`.
Its path is the latest non-empty `main_root`, so a project that moved shows where it lives now.
"""

from __future__ import annotations

import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from vague.sdk.core.events import event_ts, read_events
from vague.sdk.core.logging import get_logger
from vague.sdk.core.memory import load_ledger, vague_home

GIT_TIMEOUT_S = 2
# "ship" is the pre-rename name, still present in events logged before the rename.
SHIP_SKILLS = {"ship", "dev-ship"}


def collect_status() -> list[dict]:
    """One row per project, most recently active first.

    Row: {slug, path, path_state, branch, dirty, last_seen, last_event, inflight_designs, memories}
    path_state: live | stale | unknown
    """
    by_repo: dict[str, list[tuple[datetime, dict]]] = {}
    for event in read_events():
        moment = event_ts(value=event.get("ts"))
        if event.get("repo") and moment:
            by_repo.setdefault(str(event["repo"]), []).append((moment, event))
    memories = Counter(m.scope for m in load_ledger() if m.status == "active" and m.text)
    for scope in memories.keys() - by_repo.keys() - {"global"}:
        by_repo[scope] = []
    rows = [_project_row(slug=slug, events=sorted(events, key=lambda pair: pair[0]), memories=memories[slug])
            for slug, events in by_repo.items()]
    # A scope with memories but no events has no last_seen and sorts last.
    rows.sort(key=lambda r: r["last_seen"] or "", reverse=True)
    return rows


def _project_row(slug: str, events: list[tuple[datetime, dict]], memories: int) -> dict:
    path = next((str(e["main_root"]) for _, e in reversed(events) if e.get("main_root")), None)
    starts = [(ts, e) for ts, e in events if e.get("event") == "skill_start" and e.get("skill")]
    last_start = starts[-1] if starts else None
    last_ship = max((ts for ts, e in starts if e["skill"] in SHIP_SKILLS), default=None)
    row: dict = {
        "slug": slug,
        "path": path,
        "path_state": "unknown",
        "branch": None,
        "dirty": None,
        "last_seen": events[-1][0].isoformat() if events else None,
        "last_event": {"skill": last_start[1]["skill"], "event": "skill_start", "ts": last_start[0].isoformat()}
        if last_start else None,
        "inflight_designs": _count_inflight_designs(designs=vague_home() / "projects" / slug / "designs",
                                                    last_ship=last_ship),
        "memories": memories,
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


def _count_inflight_designs(designs: Path, last_ship: datetime | None) -> int:
    """Design docs modified after the last dev-ship start: plans not yet shipped."""
    if not designs.is_dir():
        return 0
    return sum(1 for doc in designs.glob("*.md")
               if last_ship is None or datetime.fromtimestamp(doc.stat().st_mtime, tz=UTC) > last_ship)
