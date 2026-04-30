"""vague plan commands."""

from __future__ import annotations

import json
import sys

import typer

from vague.sdk.core.slug import get_slug
from vague.sdk.core.planning import (
    get_state,
    set_state,
    list_plans,
    get_plan_status,
    complete_plan,
)


def cmd_plan_list(phase: str) -> None:
    """List plans in a phase. Outputs JSON array."""
    slug = get_slug()
    plans = list_plans(slug, phase)
    typer.echo(json.dumps(plans, default=str))


def cmd_plan_status(plan_id: str) -> None:
    """Get plan frontmatter. Outputs JSON."""
    slug = get_slug()
    status = get_plan_status(slug, plan_id)
    typer.echo(json.dumps(status, default=str))


def cmd_plan_complete(plan_id: str) -> None:
    """Mark a plan as completed."""
    try:
        slug = get_slug()
        complete_plan(slug, plan_id)
        typer.echo("OK")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)


def cmd_state_get(key: str) -> None:
    """Get a state value. Outputs raw value."""
    slug = get_slug()
    value = get_state(slug, key)
    typer.echo(str(value) if value is not None else "null")


def cmd_state_set(key: str, value: str) -> None:
    """Set a state value."""
    try:
        slug = get_slug()
        set_state(slug, key, value)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)
