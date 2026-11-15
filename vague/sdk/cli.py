"""vague CLI - main Typer app."""

from __future__ import annotations

import sys
import time
from typing import Annotated

import typer

from vague.installer import cmd_install, cmd_uninstall
from vague.sdk.commands.commit import cmd_commit
from vague.sdk.commands.config import cmd_config_get, cmd_config_set
from vague.sdk.commands.design import cmd_design_check
from vague.sdk.commands.events import cmd_log_event
from vague.sdk.commands.init import cmd_context
from vague.sdk.commands.memory import cmd_memory_log, cmd_memory_search
from vague.sdk.commands.skill import (
    cmd_skill_add,
    cmd_skill_check,
    cmd_skill_list,
)
from vague.sdk.commands.slug import cmd_slug
from vague.sdk.commands.status import cmd_status
from vague.sdk.commands.ui import cmd_ui
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
    files: Annotated[list[str] | None, typer.Option(
        "--files", help="A file the memory touches or a skill wrote, in or outside the repo. Repeat it, or use commas.",
    )] = None,
    use_global: Annotated[bool, typer.Option("--global", help="Holds in every repo: scope global.")] = False,
    about: Annotated[str | None, typer.Option("--about", help="Feedback about this skill (observation).")] = None,
    status: Annotated[str | None, typer.Option("--status", help="active|forgotten|actioned|declined")] = None,
    scratch: Annotated[bool, typer.Option(
        "--scratch", help="A note for this project's other agents (kind note), hidden after 7 days.")] = False,
    doc: Annotated[bool, typer.Option(
        "--doc", help="A pointer to a document a skill wrote (kind doc). Needs --files <path>.")] = False,
    skill: Annotated[str | None, typer.Option("--skill", help="The skill writing this memory.")] = None,
) -> None:
    """Log a memory to the global ledger. Re-using a key supersedes it.

    Kinds: learning (default), observation (--about), note (--scratch), doc (--doc).
    """
    cmd_memory_log(key=key, text=text, files=files, use_global=use_global, about=about, status=status,
                   scratch=scratch, skill=skill, doc=doc)


@sdk_app.command("memory-search")
def memory_search(
    words: Annotated[list[str] | None, typer.Argument(help="Words to match; none lists every memory.")] = None,
    scope: Annotated[str | None, typer.Option(
        "--scope", help="A project scope, global, or all. Default: this scope plus global.")] = None,
    kind: Annotated[str | None, typer.Option("--kind", help="learning|observation|note|doc")] = None,
    scratch: Annotated[bool, typer.Option("--scratch", help="Only notes: shorthand for --kind note.")] = False,
    skill: Annotated[str | None, typer.Option("--skill", help="Only memories this skill wrote (exact match).")] = None,
) -> None:
    """Print memories that contain every word across key, text, files and skill, newest first."""
    cmd_memory_search(words=words or [], scope=scope, kind=kind, scratch=scratch, skill=skill)


@sdk_app.command("ui")
def ui(
    port: Annotated[int, typer.Option("--port", help="Port on 127.0.0.1.")] = 8765,
    no_open: Annotated[bool, typer.Option("--no-open", help="Do not open the browser.")] = False,
) -> None:
    """Serve the usage graph (projects, branches, skills, memories, files) on localhost."""
    cmd_ui(port=port, open_browser=not no_open)


@sdk_app.command("slug")
def slug() -> None:
    """Output SLUG=... and BRANCH=..."""
    cmd_slug()


@sdk_app.command("log-event")
def log_event() -> None:
    """Record a Claude Code hook event (reads hook JSON on stdin)."""
    cmd_log_event()


@sdk_app.command("design-check")
def design_check(
    paths: Annotated[list[str] | None, typer.Argument(help="UI files or directories to scan (recursive).")] = None,
    hook: Annotated[bool, typer.Option(
        "--hook", help="Read a PostToolUse payload on stdin and check the edited file; exit 2 on findings.")] = False,
) -> None:
    """Scan UI source files for AI-design tells (Impeccable's 8 source rules). Exits 1 on any finding.

    Brand fonts named in this project's `design-type` learning are never flagged.
    No path is a usage error (exit 2).
    """
    cmd_design_check(paths=paths or [], hook=hook)


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


@sdk_app.command("skill-check")
def skill_check(paths: Annotated[list[str] | None, typer.Argument()] = None) -> None:
    """Check skills against the skill rules; no path checks every skill and the docs. Exits 1 on any finding."""
    cmd_skill_check(paths=paths or [])


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
