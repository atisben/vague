"""vague learnings-log / learnings-search commands."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import typer

from vague.models import LearningEntry
from vague.sdk.core.slug import get_slug
from vague.sdk.core.learnings import append_learning, search_learnings


def cmd_learnings_log(json_input: str) -> None:
    """Append a learning entry. Input: JSON string of LearningEntry fields."""
    try:
        data = json.loads(json_input)
        if "ts" not in data:
            data["ts"] = datetime.now(timezone.utc).isoformat()
        entry = LearningEntry(**data)
        slug = get_slug()
        append_learning(slug, entry)
        typer.echo("OK")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)


def cmd_learnings_search(
    type_filter: str | None = None,
    min_confidence: int = 0,
) -> None:
    """Search learnings. Outputs JSON array."""
    try:
        slug = get_slug()
        entries = search_learnings(slug, type_filter=type_filter, min_confidence=min_confidence)
        result = [json.loads(e.model_dump_json()) for e in entries]
        typer.echo(json.dumps(result, default=str))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)
