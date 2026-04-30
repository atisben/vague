"""vague slug command."""

from __future__ import annotations

import typer

from vague.sdk.core.slug import get_slug, get_branch


def cmd_slug() -> None:
    """Output SLUG and BRANCH."""
    slug = get_slug()
    branch = get_branch()
    typer.echo(f"SLUG={slug}")
    typer.echo(f"BRANCH={branch}")
