"""vague status command — cross-project dashboard."""

from __future__ import annotations

import json
import sys

import typer
from rich.console import Console
from rich.table import Table

from vague.sdk.core.status import collect_status

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
    table.add_column("Branch")
    table.add_column("Git")
    table.add_column("Last activity")
    table.add_column("In-flight plans", justify="right")
    table.add_column("Learnings", justify="right")

    for row in rows:
        table.add_row(
            row["slug"],
            row["branch"] or "—",
            _git_cell(row),
            _activity_cell(row),
            str(row["inflight_designs"]) if row["inflight_designs"] else "—",
            str(row["learnings"]) if row["learnings"] else "—",
        )

    console.print(table)

    inflight = [r for r in rows if r["inflight_designs"]]
    if inflight:
        names = ", ".join(r["slug"] for r in inflight)
        console.print(f"[yellow]{len(inflight)} project(s) with unshipped plans:[/yellow] {names}")


def _git_cell(row: dict) -> str:
    if row["path_state"] == "stale":
        return "[red]path stale[/red]"
    if row["path_state"] == "unknown":
        return "[dim]unknown (run a skill here once)[/dim]"
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
