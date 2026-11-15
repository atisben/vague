"""Cross-project status for `vague status`, derived from the events log and the memory ledger.

A project is any `repo` that appears in an event, or any ledger scope except `global`.
Its path is the latest non-empty `main_root`, so a project that moved shows where it lives now.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from vague import git
from vague.events import event_ts, read_events
from vague.memory import Memory, load_ledger

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
    ledger = load_ledger()
    memories = Counter(m.scope for m in ledger if m.status == "active" and m.text)
    for scope in memories.keys() - by_repo.keys() - {"global"}:
        by_repo[scope] = []
    rows = [_project_row(slug=slug, events=sorted(events, key=lambda pair: pair[0]), memories=memories[slug],
                         ledger=ledger)
            for slug, events in by_repo.items()]
    # A scope with memories but no events has no last_seen and sorts last.
    rows.sort(key=lambda r: r["last_seen"] or "", reverse=True)
    return rows


def _project_row(slug: str, events: list[tuple[datetime, dict]], memories: int, ledger: list[Memory]) -> dict:
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
        "inflight_designs": _count_inflight_designs(ledger=ledger, scope=slug, last_ship=last_ship),
        "memories": memories,
    }
    if path:
        repo = Path(path)
        if repo.is_dir():
            row["path_state"] = "live"
            row["branch"] = git.run("branch", "--show-current", cwd=repo, timeout=GIT_TIMEOUT_S)
            porcelain = git.run("status", "--porcelain", cwd=repo, timeout=GIT_TIMEOUT_S)
            row["dirty"] = bool(porcelain) if porcelain is not None else None
        else:
            row["path_state"] = "stale"
    return row


def _count_inflight_designs(ledger: list[Memory], scope: str, last_ship: datetime | None) -> int:
    """/plan-eng doc memories of this scope logged after the last dev-ship start: plans not yet shipped.

    A doc key carries the branch, so re-planning a branch supersedes its pointer instead of adding one.
    """
    return sum(1 for m in ledger
               if m.scope == scope and m.kind == "doc" and m.skill == "plan-eng" and m.status == "active"
               and (last_ship is None or m.ts > last_ship))


console = Console()


def cmd_status(as_json: bool = False) -> None:
    """Show a cross-project dashboard. Rich table by default, JSON with --json."""
    try:
        rows = collect_status()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from e

    if as_json:
        typer.echo(json.dumps(rows, default=str))
        return

    if not rows:
        typer.echo("No projects yet — run any skill inside a repo.")
        return

    table = Table(title="vague status")
    table.add_column("Project", style="cyan")
    table.add_column("Path")
    table.add_column("Branch")
    table.add_column("Git")
    table.add_column("Last activity")
    table.add_column("In-flight designs", justify="right")
    table.add_column("Memories", justify="right")

    for row in rows:
        table.add_row(
            row["slug"],
            row["path"] or "-",
            row["branch"] or "—",
            _git_cell(row),
            _activity_cell(row),
            str(row["inflight_designs"]) if row["inflight_designs"] else "—",
            str(row["memories"]) if row["memories"] else "—",
        )

    console.print(table)

    inflight = [r for r in rows if r["inflight_designs"]]
    if inflight:
        names = ", ".join(r["slug"] for r in inflight)
        console.print(f"[yellow]{len(inflight)} project(s) with unshipped designs:[/yellow] {names}")


def _git_cell(row: dict) -> str:
    if row["path_state"] == "stale":
        return "[red]path stale[/red]"
    if row["path_state"] == "unknown":
        return "[dim]path unknown (run a skill there once)[/dim]"
    if row["dirty"] is None:
        return "[dim]git unavailable[/dim]"
    return "[yellow]dirty[/yellow]" if row["dirty"] else "[green]clean[/green]"


def _activity_cell(row: dict) -> str:
    last_seen = (row["last_seen"] or "")[:10]
    event = row["last_event"]
    if event and event.get("skill"):
        suffix = f" ({event['skill']})"
    else:
        suffix = ""
    return (last_seen or "—") + suffix
