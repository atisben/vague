"""vague timeline-log command."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import typer

from vague.models import TimelineEntry
from vague.sdk.core.slug import get_slug
from vague.sdk.core.timeline import append_timeline


def cmd_timeline_log(json_input: str) -> None:
    """Append a timeline entry. Input: JSON string of TimelineEntry fields."""
    try:
        data = json.loads(json_input)
        if "ts" not in data:
            data["ts"] = datetime.now(timezone.utc).isoformat()
        if "session" not in data:
            data["session"] = "unknown"
        if "branch" not in data:
            data["branch"] = "unknown"
        entry = TimelineEntry(**data)
        slug = get_slug()
        append_timeline(slug, entry)
        typer.echo("OK")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)
