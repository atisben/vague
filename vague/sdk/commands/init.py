"""vague init command."""

from __future__ import annotations

import shlex
import sys

import typer

from vague.models import ConfigModel, VagueInitResult
from vague.sdk.core.analytics import record_skill_start
from vague.sdk.core.config import get_config
from vague.sdk.core.learnings import get_top_learnings
from vague.sdk.core.logging import get_logger
from vague.sdk.core.projects import upsert_project_meta
from vague.sdk.core.slug import get_branch, get_repo_root, get_slug


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



def _record_usage(skill: str, slug: str, branch: str, telemetry: str) -> None:
    """Mechanical telemetry: usage event + project path, best-effort.

    Must never propagate — a skill preamble that fails to log must still get
    its context output (the keystone property of context/init).

    `telemetry: off` disables the usage event; project.md is structural
    (it powers `vague status`, like timeline.md) and is always written.
    """
    if telemetry != "off":
        try:
            record_skill_start(skill=skill, slug=slug, branch=branch)
        except Exception as e:
            get_logger().warning("usage capture failed for %s: %s", skill, e)
    try:
        upsert_project_meta(slug=slug, path=get_repo_root())
    except Exception as e:
        get_logger().warning("project meta upsert failed for %s: %s", slug, e)


def cmd_context(shell: bool = False, skill: str | None = None) -> None:
    """Print project context for skill preambles.

    With --shell, emit eval-able assignments so a skill can do
    `eval "$(vague context --shell --skill <name>)"` instead of spawning
    python3 three times. Without --shell, behaves like `vague init` (JSON).
    With --skill, logs a usage event and records the repo path as a
    best-effort side effect before printing.
    """
    if not shell:
        if skill is not None:
            try:
                _record_usage(skill, get_slug(), get_branch(), get_config().telemetry)
            except Exception as e:
                get_logger().warning("usage capture failed: %s", e)
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

    if skill is not None:
        _record_usage(skill, slug, branch, str(config.telemetry))

    lines = [
        f"SLUG={shlex.quote(slug)}",
        f"BRANCH={shlex.quote(branch)}",
        f"PROACTIVE={shlex.quote(str(config.proactive))}",
        f"TELEMETRY={shlex.quote(str(config.telemetry))}",
    ]
    typer.echo("\n".join(lines))
