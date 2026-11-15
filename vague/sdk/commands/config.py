"""vague config-get / config-set commands."""

from __future__ import annotations

import sys

import typer

from vague.config import get_config, load_config, set_config_key


def cmd_config_get(key: str) -> None:
    """Print a config value: the file's value, else the default, else 'null'."""
    value = {**get_config().model_dump(), **load_config()}.get(key)
    typer.echo("null" if value is None else str(value))


def cmd_config_set(key: str, value: str) -> None:
    """Set a config value in config.env."""
    try:
        set_config_key(key=key, value=value)
    except OSError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from e
