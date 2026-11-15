"""vague log-event command: record a Claude Code hook event."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import typer

from vague.hooks import edited_file
from vague.sdk.core.logging import get_logger


def _bundled_skills_root() -> Path:
    """Resolved directory of the skills shipped in this repo. Tests patch it to a tmp dir."""
    from vague.sdk.core.skill_rules import default_repo_root
    return (default_repo_root() / "vague" / "assets" / "skills").resolve()


def _edited_skill_dir(payload: dict[str, Any]) -> Path | None:
    """The bundled skill a Write/Edit touched, or None.

    Only dirs under the bundled root qualify: a hook must not run the rules on any
    SKILL.md the user happens to edit elsewhere on disk.
    """
    resolved = edited_file(payload=payload)
    root = _bundled_skills_root()
    if resolved is None or not resolved.is_relative_to(root):
        return None

    from vague.sdk.core.skill_rules import skill_dir_for
    skill_dir = skill_dir_for(path=resolved)
    if skill_dir is None or skill_dir == root or not skill_dir.is_relative_to(root):
        return None
    return skill_dir


def cmd_log_event() -> None:
    """Read hook JSON on stdin, append an event, and check edited bundled skills.

    Runs on every Skill tool call, Write, Edit and prompt, so it never prints to stdout
    and exits 0 on any failure: a broken log must not slow or break the user's session.
    The one exception is a skill check with findings: exit 2 sends stderr back to Claude.
    """
    payload: dict[str, Any] | None = None
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            get_logger().warning("log-event: payload is not a JSON object")
            return
        payload = parsed

        from vague.config import get_config
        if get_config().telemetry != "off":
            from vague.sdk.core.events import append_event, parse_hook_payload
            event = parse_hook_payload(payload=payload)
            if event is not None:
                append_event(event=event)
    except Exception as e:
        get_logger().warning("log-event failed: %s", e)

    if payload is None:
        return

    findings: list[str] = []
    skill_dir: Path | None = None
    try:
        skill_dir = _edited_skill_dir(payload=payload)
        if skill_dir is not None:
            from vague.sdk.core import skill_rules
            findings = skill_rules.check_skill(skill_dir=skill_dir)
    except Exception as e:
        get_logger().warning("log-event skill check failed: %s", e)
        return

    # Exit outside the try blocks so `except Exception` cannot swallow it.
    if findings and skill_dir is not None:
        print(f"vague skill-check: {len(findings)} finding(s) in {skill_dir.name}", file=sys.stderr)
        for finding in findings:
            print(finding, file=sys.stderr)
        raise typer.Exit(code=2)
