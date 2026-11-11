"""Append-only event log of vague usage.

One JSON line per event in $VAGUE_HOME/events/YYYY-MM.jsonl. Only facts about
vague usage are recorded: which skill started, and which vague state file a
vague command read or wrote. Deriving which context belonged to which skill is
the reader's job, by ordering events per session.

Privacy: never project file paths, file contents, search patterns, Bash
commands, prompt text beyond a leading `/name`, or tool output. Nothing leaves
the machine.
"""

from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from vague.models import ConfigModel
from vague.sdk.core.frontmatter import read_md
from vague.sdk.core.logging import get_logger
from vague.sdk.core.slug import GitContext, get_git_context, get_repo_slug

_SLASH_RE = re.compile(r"^/([a-z0-9][a-z0-9:_-]*)")

# `vague status` reads several files per project. Without a cap, a machine with
# many projects would write hundreds of lines for one dashboard call.
MAX_STATUS_READS = 50


def _normalize_path(path: str, cwd: str) -> str:
    """Absolute, symlink-resolved path.

    Git reports symlink-resolved roots (/private/var on macOS) while a state
    path may say /var, so only a resolved path can be prefix-matched against `root`.
    """
    return os.path.realpath(os.path.join(cwd, path) if cwd else path)


class Event(BaseModel):
    ts: datetime
    session: str
    event: Literal["skill_start", "context_read", "context_write"]
    cwd: str
    repo: str
    branch: str
    root: str
    main_root: str
    is_worktree: bool
    runtime: str
    agent_id: str | None = None
    skill: str | None = None
    source: Literal["tool", "slash"] | None = None
    path: str | None = None
    command: str | None = None


def events_path(now: datetime | None = None) -> Path:
    """Monthly file, so no single log grows without bound."""
    moment = now or datetime.now(UTC)
    home = Path(os.environ.get("VAGUE_HOME", Path.home() / ".vague"))
    return home / "events" / f"{moment:%Y-%m}.jsonl"


def _runtime() -> str:
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(config_dir).name if config_dir else "claude"


def _classify(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Event-specific fields of a hook payload, or None when it is not a skill start."""
    hook = payload.get("hook_event_name")

    if hook == "UserPromptSubmit":
        prompt = payload.get("prompt")
        match = _SLASH_RE.match(prompt) if isinstance(prompt, str) else None
        if match:
            return {"event": "skill_start", "skill": match.group(1), "source": "slash"}
        return None

    if hook == "PostToolUse" and payload.get("tool_name") == "Skill":
        tool_input = payload.get("tool_input")
        tool_response = payload.get("tool_response")
        skill = tool_input.get("skill") if isinstance(tool_input, dict) else None
        failed = isinstance(tool_response, dict) and tool_response.get("success") is False
        if isinstance(skill, str) and skill and not failed:
            return {"event": "skill_start", "skill": skill, "source": "tool"}

    return None


def parse_hook_payload(payload: dict[str, Any], now: datetime | None = None) -> Event | None:
    """Turn a hook payload into an Event, or None when it is not a skill start.

    A payload now yields at most one event, so a single value says "nothing to
    record" more plainly than an empty list.
    """
    fields = _classify(payload)
    if fields is None:
        return None
    cwd = str(payload.get("cwd") or "")
    work_dir = Path(cwd) if cwd else None
    agent_id = payload.get("agent_id")
    git = get_git_context(cwd=work_dir)
    return Event(
        ts=now or datetime.now(UTC),
        session=str(payload.get("session_id") or "unknown"),
        cwd=cwd,
        repo=get_repo_slug(context=git),
        branch=git.branch,
        root=str(git.root),
        main_root=str(git.main_root),
        is_worktree=git.is_worktree,
        runtime=_runtime(),
        agent_id=agent_id if isinstance(agent_id, str) else None,
        **fields,
    )


def append_event(event: Event) -> None:
    """Append one line in a single write.

    One os.write on an O_APPEND fd lands contiguously on local filesystems, so
    concurrent hooks do not interleave their lines and need no lock. Only a
    write beyond PIPE_BUF is not guaranteed atomic, and one line stays far below it.
    """
    path = events_path(now=event.ts)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (event.model_dump_json(exclude_none=True) + "\n").encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)


# State of the current `vague` process. begin_command() resets it, so a
# CliRunner test that invokes several commands in one process sees each fresh.
_current_command: str | None = None
_git_cache: tuple[GitContext, str] | None = None
_logged: set[tuple[str, str]] = set()
_status_reads = 0


def begin_command(command: str | None) -> None:
    """Name the running vague subcommand and reset per-command state."""
    global _current_command, _git_cache, _status_reads
    _current_command = command
    _git_cache = None
    _status_reads = 0
    _logged.clear()


def _telemetry_off() -> bool:
    """Same rule as config.get_config, but silent: a bad config.md must not add stderr noise here."""
    home = Path(os.environ.get("VAGUE_HOME", Path.home() / ".vague"))
    try:
        data = read_md(home / "config.md")
        return ConfigModel(**{k: v for k, v in data.items() if k in ConfigModel.model_fields}).telemetry == "off"
    except Exception:
        return False


def _git_for_cwd() -> tuple[GitContext, str]:
    """Git context and repo slug, computed once per command.

    One command can touch several state files, and each lookup spawns git
    processes. Within one command the answer cannot change.
    """
    global _git_cache
    if _git_cache is None:
        git = get_git_context()
        _git_cache = (git, get_repo_slug(context=git))
    return _git_cache


def log_context_access(kind: Literal["read", "write"], path: Path, command: str | None = None) -> None:
    """Record that a vague command read or wrote a state file. Never raises, never prints.

    Logs nothing outside Claude Code (no session id): a manual terminal run is
    not skill activity. `log-event` is excluded so the hook never logs itself.
    """
    global _status_reads
    try:
        session = os.environ.get("CLAUDE_CODE_SESSION_ID")
        command = command or _current_command
        if not session or not command or command == "log-event":
            return
        cwd = os.getcwd()
        resolved = _normalize_path(str(path), cwd)
        # A read of a missing file pulled no context into the skill.
        if kind == "read" and not os.path.exists(resolved):
            return
        if _telemetry_off():
            return
        key = (kind, resolved)
        if key in _logged:
            return
        if kind == "read" and command == "status":
            if _status_reads >= MAX_STATUS_READS:
                return
            _status_reads += 1
        _logged.add(key)
        git, repo = _git_for_cwd()
        append_event(Event(
            ts=datetime.now(UTC),
            session=session,
            event=f"context_{kind}",
            cwd=cwd,
            repo=repo,
            branch=git.branch,
            root=str(git.root),
            main_root=str(git.main_root),
            is_worktree=git.is_worktree,
            runtime=_runtime(),
            path=resolved,
            command=command,
        ))
    except Exception as e:
        get_logger().warning("context event failed: %s", e)
