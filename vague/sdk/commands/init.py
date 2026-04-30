"""vague init command."""

from __future__ import annotations

import json
import sys

import typer

from vague.models import VagueInitResult
from vague.sdk.core.config import get_config
from vague.sdk.core.slug import get_slug, get_branch
from vague.sdk.core.learnings import get_top_learnings


def cmd_init() -> None:
    """Initialize vague context for the current project. Outputs JSON."""
    try:
        slug = get_slug()
        branch = get_branch()
        config = get_config()

        try:
            learnings = get_top_learnings(slug)
        except Exception:
            learnings = []

        result = VagueInitResult(
            slug=slug,
            branch=branch,
            proactive=config.proactive,
            telemetry=config.telemetry,
            learnings=learnings,
        )
        typer.echo(result.model_dump_json())
    except Exception as e:
        print(f"Warning: vague init error: {e}", file=sys.stderr)
        # Never fail — return defaults
        fallback = VagueInitResult(
            slug="unknown",
            branch="unknown",
            proactive=True,
            telemetry="local",
            learnings=[],
        )
        typer.echo(fallback.model_dump_json())
