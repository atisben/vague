"""vague commit command."""

from __future__ import annotations

import sys

import typer

from vague.sdk.core.git_ops import atomic_commit, NOTHING_TO_COMMIT


def cmd_commit(message: str, files: list[str]) -> None:
    """Stage and commit files. Outputs SHA or 'nothing-to-commit'."""
    try:
        sha = atomic_commit(message, files)
        typer.echo(sha)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)
