"""vague context command."""

from __future__ import annotations

import json
import shlex
import sys

import typer

from vague.models import ConfigModel
from vague.sdk.core.config import get_config
from vague.sdk.core.events import log_context_access
from vague.sdk.core.logging import get_logger
from vague.sdk.core.memory import changed_files, ledger_path, render_block, scratch_path
from vague.sdk.core.slug import get_branch, get_scope, get_slug

_DELIMITER = "VAGUE_MEMORY"


def cmd_context(shell: bool = False, skill: str | None = None) -> None:
    """Print project context for skill preambles.

    With --shell, emit eval-able assignments so a skill can do
    `eval "$(vague context --shell --skill <name>)"`. Without --shell, print the
    same fields as one JSON object. --skill only ranks the memory block.
    """
    try:
        slug = get_slug()
        branch = get_branch()
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
            "proactive": config.proactive,
            "telemetry": config.telemetry,
            "memory": "\n".join(memory or []),
        }))
        return

    lines = [
        f"SLUG={shlex.quote(slug)}",
        f"BRANCH={shlex.quote(branch)}",
        f"PROACTIVE={shlex.quote(str(config.proactive))}",
        f"TELEMETRY={shlex.quote(str(config.telemetry))}",
    ]
    # The quoted heredoc delimiter stops the shell from expanding `$` or backticks in memory text.
    heredoc = [f"cat <<'{_DELIMITER}'", *memory, _DELIMITER] if memory is not None else []
    typer.echo("\n".join(lines + heredoc))


def _memory_lines(skill: str | None) -> list[str] | None:
    """The memory block lines for this scope, or None on any error so the preamble still prints."""
    try:
        scope = get_scope()
        block = render_block(scope=scope, skill=skill, changed_files=changed_files())
        content = [line for line in block.text.splitlines() if line != _DELIMITER]
        if block.ids:
            log_context_access(kind="read", path=ledger_path(), ids=block.ids)
        if block.scratch_ids and scope:
            log_context_access(kind="read", path=scratch_path(scope=scope), ids=block.scratch_ids)
        return content
    except Exception as e:
        get_logger().warning("memory block failed: %s", e)
        return None
