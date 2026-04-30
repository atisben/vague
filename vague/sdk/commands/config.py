"""vague config-get / config-set commands."""

from __future__ import annotations

import sys
from typing import Any

import typer

from vague.sdk.core.config import get_config, set_config_key


def cmd_config_get(key: str) -> None:
    """Get a config value by key. Outputs raw value or 'null'."""
    try:
        config = get_config()
        data = config.model_dump()
        value = data.get(key)
        if value is None:
            typer.echo("null")
        else:
            typer.echo(str(value))
    except Exception:
        typer.echo("null")


def cmd_config_set(key: str, value: str) -> None:
    """Set a config value. Coerces booleans."""
    try:
        # Coerce booleans
        parsed: Any = value
        if value.lower() == "true":
            parsed = True
        elif value.lower() == "false":
            parsed = False
        set_config_key(key, parsed)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)
