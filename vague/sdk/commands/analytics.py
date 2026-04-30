"""vague analytics-log / analytics-show commands."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import typer
from rich.console import Console
from rich.table import Table

from vague.models import AnalyticsEntry
from vague.sdk.core.analytics import append_analytics, get_analytics


console = Console()


def cmd_analytics_log(json_input: str) -> None:
    """Append an analytics entry. Input: JSON string of AnalyticsEntry fields."""
    try:
        data = json.loads(json_input)
        if "ts" not in data:
            data["ts"] = datetime.now(timezone.utc).isoformat()
        entry = AnalyticsEntry(**data)
        append_analytics(entry)
        typer.echo("OK")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)


def cmd_analytics_show(window: str = "7d", as_json: bool = False) -> None:
    """Show analytics data. Rich table by default, JSON with --json."""
    try:
        entries = get_analytics(window)
        if as_json:
            result = [json.loads(e.model_dump_json()) for e in entries]
            typer.echo(json.dumps(result, default=str))
            return

        if not entries:
            typer.echo(f"No analytics data for window: {window}")
            return

        # Aggregate by skill
        counts: dict[str, int] = {}
        for e in entries:
            counts[e.skill] = counts.get(e.skill, 0) + 1

        table = Table(title=f"Skill Usage ({window})")
        table.add_column("Skill", style="cyan")
        table.add_column("Runs", justify="right", style="green")

        for skill, count in sorted(counts.items(), key=lambda x: x[1], reverse=True):
            table.add_row(skill, str(count))

        console.print(table)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)
