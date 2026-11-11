"""vague CLI - main Typer app."""

from __future__ import annotations

import sys
import time
from typing import Annotated

import typer

from vague.installer import cmd_install, cmd_uninstall
from vague.sdk.commands.commit import cmd_commit
from vague.sdk.commands.config import cmd_config_get, cmd_config_set
from vague.sdk.commands.events import cmd_log_event
from vague.sdk.commands.init import cmd_context
from vague.sdk.commands.memory import cmd_memory_log, cmd_memory_search
from vague.sdk.commands.migrate import cmd_migrate
from vague.sdk.commands.skill import (
    cmd_skill_add,
    cmd_skill_audit,
    cmd_skill_list,
    cmd_skill_validate,
)
from vague.sdk.commands.slug import cmd_slug
from vague.sdk.commands.status import cmd_status
from vague.sdk.core.events import begin_command
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
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Show version and exit."),
    ] = False,
) -> None:
    """Python CLI layer for LLM skill-based AI workflows."""
    # Core helpers log state-file access under the typer command name.
    begin_command(command=ctx.invoked_subcommand)


@sdk_app.command("install")
def install(
    runtime: Annotated[
        str | None,
        typer.Option("--runtime", help="claude|claude:<profile>|cursor|windsurf|generic"),
    ] = None,
) -> None:
    """Install skills into your LLM runtime (e.g. ~/.claude/skills/)."""
    cmd_install(runtime=runtime)


@sdk_app.command("uninstall")
def uninstall(
    runtime: Annotated[
        str | None,
        typer.Option("--runtime", help="claude|claude:<profile>|cursor|windsurf|generic"),
    ] = None,
) -> None:
    """Remove vague skills from your LLM runtime."""
    cmd_uninstall(runtime=runtime)


@sdk_app.command("context")
def context(
    shell: Annotated[
        bool, typer.Option("--shell", help="Emit eval-able SLUG=/BRANCH=/PROACTIVE=/TELEMETRY= lines.")
    ] = False,  # noqa: E501
    skill: Annotated[
        str | None, typer.Option("--skill", help="Rank the memory block for this skill.")
    ] = None,  # noqa: E501
) -> None:
    """Print project context for skill preambles. JSON by default, shell vars with --shell."""
    cmd_context(shell=shell, skill=skill)


@sdk_app.command("status")
def status(
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Cross-project dashboard: branches, in-flight designs, last activity."""
    cmd_status(as_json=as_json)


@sdk_app.command("config-get")
def config_get(key: str) -> None:
    """Get a config value by key."""
    cmd_config_get(key)


@sdk_app.command("config-set")
def config_set(key: str, value: str) -> None:
    """Set a config value."""
    cmd_config_set(key, value)


@sdk_app.command("memory-log")
def memory_log(
    key: str,
    text: Annotated[str | None, typer.Argument(help="The fact, at most 600 characters.")] = None,
    files: Annotated[str | None, typer.Option("--files", help="Comma-separated repo-relative paths.")] = None,
    use_global: Annotated[bool, typer.Option("--global", help="Holds in every repo: scope global.")] = False,
    about: Annotated[str | None, typer.Option("--about", help="Feedback about this skill (observation).")] = None,
    status: Annotated[str | None, typer.Option("--status", help="active|forgotten|actioned|declined")] = None,
    scratch: Annotated[bool, typer.Option("--scratch", help="Write to the scope's shared scratchpad.")] = False,
    skill: Annotated[str | None, typer.Option("--skill", help="The skill writing this learning.")] = None,
) -> None:
    """Log a memory to the global ledger. Re-using a key supersedes it."""
    cmd_memory_log(key=key, text=text, files=files, use_global=use_global, about=about, status=status,
                   scratch=scratch, skill=skill)


@sdk_app.command("memory-search")
def memory_search(
    words: Annotated[list[str] | None, typer.Argument(help="Words to match; none lists every memory.")] = None,
    scope: Annotated[str | None, typer.Option(
        "--scope", help="A project scope, global, or all. Default: this scope plus global.")] = None,
    kind: Annotated[str | None, typer.Option("--kind", help="learning|observation")] = None,
    scratch: Annotated[bool, typer.Option("--scratch", help="Search scratchpads instead of the ledger.")] = False,
) -> None:
    """Print memories that contain every word across key, text, files and skill, newest first."""
    cmd_memory_search(words=words or [], scope=scope, kind=kind, scratch=scratch)


@sdk_app.command("migrate")
def migrate(
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Print counts and mappings, write nothing.")] = False,
    archive: Annotated[bool, typer.Option("--archive", help="Move the old stores to archive/<date>/.")] = False,
) -> None:
    """Move old per-project learnings, observations, timeline and project.md into the ledger and events."""
    cmd_migrate(dry_run=dry_run, do_archive=archive)


@sdk_app.command("slug")
def slug() -> None:
    """Output SLUG=... and BRANCH=..."""
    cmd_slug()


@sdk_app.command("log-event")
def log_event() -> None:
    """Record a Claude Code hook event (reads hook JSON on stdin)."""
    cmd_log_event()


@sdk_app.command("commit")
def commit(
    message: str,
    files: Annotated[list[str], typer.Option("--files", "-f")] = [],  # noqa: B006  Typer reads this default to build the option; not mutated.
) -> None:
    """Stage and commit files. Outputs SHA or 'nothing-to-commit'."""
    cmd_commit(message, files)


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
