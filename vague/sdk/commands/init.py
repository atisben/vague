"""vague init command."""

from __future__ import annotations

import json
import shlex
import sys

import typer

from vague.models import VagueInitResult, ConfigModel
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



def cmd_context(shell: bool = False) -> None:
    """Print project context for skill preambles.

    With --shell, emit eval-able assignments so a skill can do
    `eval "$(vague context --shell)"` instead of spawning python3 three times.
    Without --shell, behaves like `vague init` (JSON).
    """
    if not shell:
        cmd_init()
        return

    try:
        slug = get_slug()
        branch = get_branch()
        config = get_config()
    except Exception as e:
        print(f"Warning: vague context error: {e}", file=sys.stderr)
        slug, branch = "unknown", "unknown"
        config = ConfigModel()

    lines = [
        f"SLUG={shlex.quote(slug)}",
        f"BRANCH={shlex.quote(branch)}",
        f"PROACTIVE={shlex.quote(str(config.proactive))}",
        f"TELEMETRY={shlex.quote(str(config.telemetry))}",
    ]
    typer.echo("\n".join(lines))
