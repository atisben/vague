"""vague CLI - main Typer app."""

from __future__ import annotations

import sys
import time
from typing import Annotated

import typer

from vague.installer import cmd_install, cmd_uninstall
from vague.sdk.commands.analytics import cmd_analytics_log, cmd_analytics_show
from vague.sdk.commands.commit import cmd_commit
from vague.sdk.commands.config import cmd_config_get, cmd_config_set
from vague.sdk.commands.init import cmd_context, cmd_init
from vague.sdk.commands.learnings import cmd_learnings_log, cmd_learnings_search
from vague.sdk.commands.observations import (
    cmd_observations_list,
    cmd_observations_log,
    cmd_observations_update,
)
from vague.sdk.commands.plan import (
    cmd_plan_complete,
    cmd_plan_list,
    cmd_plan_status,
    cmd_state_get,
    cmd_state_set,
)
from vague.sdk.commands.skill import (
    cmd_skill_add,
    cmd_skill_audit,
    cmd_skill_list,
    cmd_skill_validate,
)
from vague.sdk.commands.slug import cmd_slug
from vague.sdk.commands.status import cmd_status
from vague.sdk.commands.timeline import cmd_timeline_log
from vague.sdk.core.logging import get_logger

sdk_app = typer.Typer(
    name="vague",
    help="Python CLI layer for LLM skill-based AI workflows.",
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        from importlib.metadata import PackageNotFoundError, version
        try:
            typer.echo(version("vague"))
        except PackageNotFoundError:
            typer.echo("0.1.0")
        raise typer.Exit()


@sdk_app.callback()
def _main(
    version: Annotated[
        bool,
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Show version and exit."),
    ] = False,
) -> None:
    """Python CLI layer for LLM skill-based AI workflows."""


@sdk_app.command("install")
def install(
    runtime: Annotated[str | None, typer.Option("--runtime", help="claude|copilot|cursor|windsurf|generic")] = None,
) -> None:
    """Install skills into your LLM runtime (e.g. ~/.claude/skills/)."""
    cmd_install(runtime=runtime)


@sdk_app.command("uninstall")
def uninstall(
    runtime: Annotated[str | None, typer.Option("--runtime", help="claude|copilot|cursor|windsurf|generic")] = None,
) -> None:
    """Remove vague skills from your LLM runtime."""
    cmd_uninstall(runtime=runtime)


@sdk_app.command("context")
def context(
    shell: Annotated[bool, typer.Option("--shell", help="Emit eval-able SLUG=/BRANCH=/PROACTIVE=/TELEMETRY= lines.")] = False,  # noqa: E501
    skill: Annotated[str | None, typer.Option("--skill", help="Log a usage event for this skill (mechanical telemetry).")] = None,  # noqa: E501
) -> None:
    """Print project context for skill preambles. JSON by default, shell vars with --shell."""
    cmd_context(shell=shell, skill=skill)


@sdk_app.command("status")
def status(
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Cross-project dashboard: branches, in-flight plans, last activity."""
    cmd_status(as_json=as_json)


@sdk_app.command("init")
def init() -> None:
    """Initialize vague context. Outputs JSON."""
    cmd_init()


@sdk_app.command("config-get")
def config_get(key: str) -> None:
    """Get a config value by key."""
    cmd_config_get(key)


@sdk_app.command("config-set")
def config_set(key: str, value: str) -> None:
    """Set a config value."""
    cmd_config_set(key, value)


@sdk_app.command("learnings-log")
def learnings_log(json_input: str) -> None:
    """Append a learning entry (JSON string)."""
    cmd_learnings_log(json_input)


@sdk_app.command("learnings-search")
def learnings_search(
    type: Annotated[str | None, typer.Option("--type", "-t")] = None,
    min_confidence: Annotated[int, typer.Option("--min-confidence")] = 0,
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Search learnings. Outputs JSON array (--json accepted for compatibility)."""
    cmd_learnings_search(type_filter=type, min_confidence=min_confidence)


@sdk_app.command("analytics-log")
def analytics_log(json_input: str) -> None:
    """Append an analytics entry (JSON string)."""
    cmd_analytics_log(json_input)


@sdk_app.command("analytics-show")
def analytics_show(
    window: Annotated[str, typer.Argument()] = "7d",
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Show skill usage analytics."""
    cmd_analytics_show(window=window, as_json=as_json)


@sdk_app.command("observations-log")
def observations_log(json_input: str) -> None:
    """Append an observation entry (JSON string)."""
    cmd_observations_log(json_input)


@sdk_app.command("observations-list")
def observations_list(
    status: Annotated[str | None, typer.Option("--status", "-s")] = None,
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """List observations. Outputs JSON array."""
    cmd_observations_list(status_filter=status, as_json=as_json)


@sdk_app.command("observations-update")
def observations_update(obs_id: int, status: str) -> None:
    """Update an observation's status (open|actioned|declined)."""
    cmd_observations_update(obs_id, status)


@sdk_app.command("slug")
def slug() -> None:
    """Output SLUG=... and BRANCH=..."""
    cmd_slug()


@sdk_app.command("timeline-log")
def timeline_log(json_input: str) -> None:
    """Append a timeline entry (JSON string)."""
    cmd_timeline_log(json_input)


@sdk_app.command("commit")
def commit(
    message: str,
    files: Annotated[list[str], typer.Option("--files", "-f")] = [],  # noqa: B006  Typer reads this default to build the option; not mutated.
) -> None:
    """Stage and commit files. Outputs SHA or 'nothing-to-commit'."""
    cmd_commit(message, files)


@sdk_app.command("plan-list")
def plan_list(phase: str) -> None:
    """List plans in a phase. Outputs JSON array."""
    cmd_plan_list(phase)


@sdk_app.command("plan-status")
def plan_status(plan_id: str) -> None:
    """Get plan status. Outputs JSON."""
    cmd_plan_status(plan_id)


@sdk_app.command("plan-complete")
def plan_complete(plan_id: str) -> None:
    """Mark plan as completed."""
    cmd_plan_complete(plan_id)


@sdk_app.command("state-get")
def state_get(key: str) -> None:
    """Get state value."""
    cmd_state_get(key)


@sdk_app.command("state-set")
def state_set(key: str, value: str) -> None:
    """Set state value."""
    cmd_state_set(key, value)


@sdk_app.command("skill-list")
def skill_list(
    validate: Annotated[bool, typer.Option("--validate")] = False,
) -> None:
    """List available skills."""
    cmd_skill_list(validate=validate)


@sdk_app.command("skill-validate")
def skill_validate(skill_dir: str) -> None:
    """Validate a skill directory."""
    cmd_skill_validate(skill_dir)


@sdk_app.command("skill-audit")
def skill_audit(
    skill_dir: str,
    strict: Annotated[bool, typer.Option("--strict")] = False,
) -> None:
    """Audit a skill for legacy bash patterns."""
    cmd_skill_audit(skill_dir, strict=strict)


@sdk_app.command("skill-add")
def skill_add(skill_dir: str) -> None:
    """Copy external skill to vague assets."""
    cmd_skill_add(skill_dir)


def main() -> None:
    """Entrypoint wrapper that logs each invocation (command, duration, outcome).

    Logging is off unless VAGUE_LOG is set. See vague/sdk/core/logging.py.
    """
    logger = get_logger()
    argv = sys.argv[1:]
    command = next((a for a in argv if not a.startswith("-")), "<none>")
    start = time.perf_counter()
    logger.info("start command=%s", command)
    try:
        sdk_app()
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
        elapsed = (time.perf_counter() - start) * 1000
        logger.info("end command=%s exit=%d duration_ms=%.1f", command, code, elapsed)
        raise
    except BaseException:
        elapsed = (time.perf_counter() - start) * 1000
        logger.exception("error command=%s duration_ms=%.1f", command, elapsed)
        raise
    else:
        elapsed = (time.perf_counter() - start) * 1000
        logger.info("end command=%s exit=0 duration_ms=%.1f", command, elapsed)
