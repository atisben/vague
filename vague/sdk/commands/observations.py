"""vague observations-log / observations-list / observations-update commands."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime

import typer

from vague.models import ObservationEntry
from vague.sdk.core.observations import (
    append_observation,
    list_observations,
    update_observation_status,
)
from vague.sdk.core.slug import get_slug


def cmd_observations_log(json_input: str) -> None:
    """Append an observation entry. Input: JSON string of ObservationEntry fields."""
    try:
        data = json.loads(json_input)
        slug = get_slug()
        # id is assigned atomically under lock inside append_observation;
        # supply a placeholder so model validation passes.
        data.setdefault("id", 0)
        if "ts" not in data:
            data["ts"] = datetime.now(UTC).isoformat()
        entry = ObservationEntry(**data)
        append_observation(slug, entry)
        typer.echo("OK")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from e


def cmd_observations_list(
    status_filter: str | None = None,
    as_json: bool = False,
) -> None:
    """List observations. Outputs JSON array."""
    try:
        slug = get_slug()
        entries = list_observations(slug, status_filter=status_filter)
        result = [json.loads(e.model_dump_json()) for e in entries]
        typer.echo(json.dumps(result, default=str))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from e


def cmd_observations_update(obs_id: int, status: str) -> None:
    """Update an observation's status."""
    valid_statuses = {"open", "actioned", "declined"}
    if status not in valid_statuses:
        print(f"Error: status must be one of {valid_statuses}", file=sys.stderr)
        raise typer.Exit(1)
    try:
        slug = get_slug()
        found = update_observation_status(slug, obs_id, status)
        if not found:
            print(f"Error: observation #{obs_id} not found", file=sys.stderr)
            raise typer.Exit(1)
        typer.echo("OK")
    except typer.Exit:
        raise
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from e
