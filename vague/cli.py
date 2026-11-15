"""vague CLI - main Typer app."""

from __future__ import annotations

import json
import shlex
import sys
import time
from pathlib import Path
from typing import Annotated

import typer

from vague.config import ConfigModel, get_config, load_config, set_config_key
from vague.design_rules import cmd_design_check
from vague.events import begin_command, cmd_log_event, log_context_access
from vague.git import get_git_context, get_repo_slug, get_scope
from vague.install import cmd_install, cmd_uninstall
from vague.log import get_logger
from vague.memory import changed_files, cmd_memory_log, cmd_memory_search, ledger_path, render_block
from vague.skill_rules import cmd_skill_check, cmd_skill_list
from vague.status import cmd_status
from vague.ui_server import cmd_ui
from vague.vault_scan import cmd_vault_scan, default_vault

app = typer.Typer(
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


@app.callback()
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


@app.command("install")
def install(
    runtime: Annotated[
        str | None,
        typer.Option("--runtime", help="claude (every profile) or claude:<profile>"),
    ] = None,
) -> None:
    """Install skills into your LLM runtime (e.g. ~/.claude/skills/)."""
    cmd_install(runtime=runtime)


@app.command("uninstall")
def uninstall(
    runtime: Annotated[
        str | None,
        typer.Option("--runtime", help="claude (every profile) or claude:<profile>"),
    ] = None,
) -> None:
    """Remove vague skills from your LLM runtime."""
    cmd_uninstall(runtime=runtime)


_DELIMITER = "VAGUE_MEMORY"


def _memory_lines(skill: str | None) -> list[str] | None:
    """The memory block lines for this scope, or None on any error so the preamble still prints."""
    try:
        scope = get_scope()
        block = render_block(scope=scope, skill=skill, changed_files=changed_files())
        content = [line for line in block.text.splitlines() if line != _DELIMITER]
        # One call: notes and learnings share the ledger, and a second read of the same file is deduplicated.
        if block.ids or block.scratch_ids:
            log_context_access(kind="read", path=ledger_path(), ids=[*block.scratch_ids, *block.ids])
        return content
    except Exception as e:
        get_logger().warning("memory block failed: %s", e)
        return None


@app.command("context")
def context(
    shell: Annotated[
        bool, typer.Option("--shell", help="Emit eval-able SLUG=/BRANCH=/TELEMETRY= lines.")
    ] = False,  # noqa: E501
    skill: Annotated[
        str | None, typer.Option("--skill", help="Rank the memory block for this skill.")
    ] = None,  # noqa: E501
) -> None:
    """Print project context for skill preambles. JSON by default, shell vars with --shell.

    A skill runs `eval "$(vague context --shell --skill <name>)"`. --skill only ranks the memory block.
    """
    try:
        git = get_git_context()
        slug, branch = get_repo_slug(context=git), git.branch
        config = get_config()
    except Exception as e:
        print(f"Warning: vague context error: {e}", file=sys.stderr)
        slug, branch = "unknown", "unknown"
        config = ConfigModel()

    memory = _memory_lines(skill=skill)

    if not shell:
        typer.echo(json.dumps({
            "slug": slug,
            "branch": branch,
            "telemetry": config.telemetry,
            "memory": "\n".join(memory or []),
        }))
        return

    lines = [
        f"SLUG={shlex.quote(slug)}",
        f"BRANCH={shlex.quote(branch)}",
        f"TELEMETRY={shlex.quote(str(config.telemetry))}",
    ]
    # The quoted heredoc delimiter stops the shell from expanding `$` or backticks in memory text.
    heredoc = [f"cat <<'{_DELIMITER}'", *memory, _DELIMITER] if memory is not None else []
    typer.echo("\n".join(lines + heredoc))


@app.command("status")
def status(
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Cross-project dashboard: branches, in-flight designs, last activity."""
    cmd_status(as_json=as_json)


@app.command("config-get")
def config_get(key: str) -> None:
    """Print a config value: the file's value, else the default, else 'null'."""
    value = {**get_config().model_dump(), **load_config()}.get(key)
    typer.echo("null" if value is None else str(value))


@app.command("config-set")
def config_set(key: str, value: str) -> None:
    """Set a config value in config.env."""
    try:
        set_config_key(key=key, value=value)
    except OSError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from e


@app.command("memory-log")
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


@app.command("memory-search")
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


@app.command("ui")
def ui(
    port: Annotated[int, typer.Option("--port", help="Port on 127.0.0.1.")] = 8765,
    no_open: Annotated[bool, typer.Option("--no-open", help="Do not open the browser.")] = False,
) -> None:
    """Serve the usage graph (projects, branches, skills, memories, files) on localhost."""
    cmd_ui(port=port, open_browser=not no_open)


@app.command("log-event")
def log_event() -> None:
    """Record a Claude Code hook event (reads hook JSON on stdin)."""
    cmd_log_event()


@app.command("design-check")
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


@app.command("vault-scan")
def vault_scan(
    vault: Annotated[Path | None, typer.Option(
        "--vault", help="Vault root. Default: $VAGUE_VAULT, else ~/Obsidian.")] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Print the full report as JSON.")] = False,
    similar_to: Annotated[str | None, typer.Option(
        "--similar", help="Only list live notes whose title covers these words (the /vault dedup check).")] = None,
    grace_days: Annotated[int, typer.Option(
        "--grace-days", help="Days a note stays in 9. Archive/ before it is listed as expired.")] = 90,
) -> None:
    """Inventory the Obsidian vault: hygiene issues, likely duplicates, plans, guessed kinds, expired archive.

    Measures only, never edits a note. A missing vault is a usage error (exit 2).
    """
    cmd_vault_scan(vault=vault or default_vault(), as_json=as_json, similar_to=similar_to, grace_days=grace_days)


@app.command("skill-list")
def skill_list(
    validate: Annotated[bool, typer.Option("--validate")] = False,
) -> None:
    """List available skills."""
    cmd_skill_list(validate=validate)


@app.command("skill-check")
def skill_check(paths: Annotated[list[str] | None, typer.Argument()] = None) -> None:
    """Check skills against the skill rules; no path checks every skill and the docs. Exits 1 on any finding."""
    cmd_skill_check(paths=paths or [])


def main() -> None:
    """Entrypoint wrapper that logs each invocation (command, duration, outcome).

    Logging is off unless VAGUE_LOG is set. See vague/log.py.
    """
    logger = get_logger()
    argv = sys.argv[1:]
    command = next((a for a in argv if not a.startswith("-")), "<none>")
    start = time.perf_counter()
    logger.info("start command=%s", command)
    try:
        app()
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
