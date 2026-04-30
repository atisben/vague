"""vague CLI — main Typer app."""

from __future__ import annotations

from typing import Annotated, Optional

import typer

from vague.sdk.commands.init import cmd_init
from vague.sdk.commands.config import cmd_config_get, cmd_config_set
from vague.sdk.commands.learnings import cmd_learnings_log, cmd_learnings_search
from vague.sdk.commands.analytics import cmd_analytics_log, cmd_analytics_show
from vague.sdk.commands.slug import cmd_slug
from vague.sdk.commands.timeline import cmd_timeline_log
from vague.sdk.commands.commit import cmd_commit
from vague.sdk.commands.skill import (
    cmd_skill_list,
    cmd_skill_validate,
    cmd_skill_audit,
    cmd_skill_add,
)
from vague.sdk.commands.plan import (
    cmd_plan_list,
    cmd_plan_status,
    cmd_plan_complete,
    cmd_state_get,
    cmd_state_set,
)

sdk_app = typer.Typer(
    name="vague",
    help="Python CLI layer for LLM skill-based AI workflows.",
    no_args_is_help=True,
)


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
    type: Annotated[Optional[str], typer.Option("--type", "-t")] = None,
    min_confidence: Annotated[int, typer.Option("--min-confidence")] = 0,
) -> None:
    """Search learnings. Outputs JSON array."""
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
    files: Annotated[list[str], typer.Option("--files", "-f")] = [],
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
