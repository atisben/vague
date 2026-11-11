"""Tests for vague.sdk.core.events."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from vague.sdk.core.events import Event, append_event, events_path, parse_hook_payload

NOW = datetime(2026, 11, 11, 10, 0, 0, tzinfo=UTC)


def _payload(**overrides):
    base = {"session_id": "s1", "cwd": "/nonexistent/dir/for/tests", "transcript_path": "/x.jsonl"}
    base.update(overrides)
    return base


def _parse(payload):
    return parse_hook_payload(payload=payload, now=NOW)


def _skill_payload(**overrides):
    return _payload(
        hook_event_name="PostToolUse", tool_name="Skill",
        tool_input={"skill": "learn"}, tool_response={"success": True, "commandName": "learn"},
        **overrides,
    )


def _event(**overrides):
    fields = {
        "ts": NOW, "session": "s1", "event": "skill_start", "cwd": "/c", "repo": "r", "branch": "b",
        "root": "/c", "main_root": "/c", "is_worktree": False, "runtime": "claude",
    }
    fields.update(overrides)
    return Event(**fields)


def test_parse_skill_tool_yields_skill_start_with_tool_source():
    event = _parse(_skill_payload())
    assert event is not None
    assert (event.event, event.skill, event.source) == ("skill_start", "learn", "tool")
    assert event.session == "s1"
    assert event.ts == NOW


def test_parse_skill_tool_failed_returns_none():
    event = _parse(_payload(
        hook_event_name="PostToolUse", tool_name="Skill",
        tool_input={"skill": "learn"}, tool_response={"success": False},
    ))
    assert event is None


def test_parse_pre_tool_use_is_ignored():
    event = _parse(_payload(
        hook_event_name="PreToolUse", tool_name="Skill", tool_input={"skill": "learn"},
    ))
    assert event is None


def test_parse_slash_prompt_stores_only_the_name():
    event = _parse(_payload(
        hook_event_name="UserPromptSubmit", prompt="/dev-ship now with my secret plan",
    ))
    assert event is not None
    assert (event.event, event.skill, event.source) == ("skill_start", "dev-ship", "slash")
    assert "secret" not in event.model_dump_json()


def test_parse_plain_prompt_returns_none():
    assert _parse(_payload(hook_event_name="UserPromptSubmit", prompt="hello")) is None


def test_parse_skill_start_never_stores_tool_content():
    event = _parse(_payload(
        hook_event_name="PostToolUse", tool_name="Skill",
        tool_input={"skill": "learn", "args": "PRIVATEARGS"},
        tool_response={"success": True, "output": "PRIVATEOUTPUT"},
    ))
    assert event is not None
    raw = event.model_dump_json()
    assert "PRIVATEARGS" not in raw and "PRIVATEOUTPUT" not in raw


# Realistic shapes from real Claude Code hook probe runs. None of them is about vague usage.
NOT_VAGUE_USAGE = {
    "write": _payload(
        hook_event_name="PostToolUse", tool_name="Write",
        tool_input={"file_path": "/work/a.txt", "content": "hello"},
        tool_response={"type": "create", "filePath": "/work/a.txt", "content": "hello"},
    ),
    "edit": _payload(
        hook_event_name="PostToolUse", tool_name="Edit",
        tool_input={"file_path": "/work/a.txt", "old_string": "hello", "new_string": "world"},
        tool_response={"filePath": "/work/a.txt", "oldString": "hello", "newString": "world"},
    ),
    "notebook_edit": _payload(
        hook_event_name="PostToolUse", tool_name="NotebookEdit",
        tool_input={"notebook_path": "/work/n.ipynb", "new_source": "x = 1"},
    ),
    "read": _payload(
        hook_event_name="PostToolUse", tool_name="Read", tool_input={"file_path": "/work/a.txt"},
        tool_response={"type": "text", "file": {"filePath": "/work/a.txt", "content": "alpha", "numLines": 1}},
    ),
    "grep": _payload(
        hook_event_name="PostToolUse", tool_name="Grep", tool_input={"pattern": "needle"},
        tool_response={"mode": "files_with_matches", "filenames": ["a.txt"], "numFiles": 1},
    ),
    "glob": _payload(
        hook_event_name="PostToolUse", tool_name="Glob", tool_input={"pattern": "*.txt"},
        tool_response={"filenames": ["a.txt", "b.txt"], "numFiles": 2},
    ),
    "bash": _payload(
        hook_event_name="PostToolUse", tool_name="Bash", tool_input={"command": "echo bash > b.txt"},
    ),
    "startup_hook": _payload(hook_event_name="SessionStart", source="startup"),
    "stop": _payload(hook_event_name="Stop", last_assistant_message="done"),
    "shutdown_hook": _payload(hook_event_name="SessionEnd"),
    "tool_failure": _payload(
        hook_event_name="PostToolUseFailure", tool_name="Read",
        tool_input={"file_path": "/work/missing.txt"}, error="File does not exist.",
    ),
    "subagent_stop": _payload(hook_event_name="SubagentStop", agent_id="a1"),
}


@pytest.mark.parametrize("payload", NOT_VAGUE_USAGE.values(), ids=NOT_VAGUE_USAGE.keys())
def test_parse_payload_unrelated_to_vague_usage_returns_none(payload):
    assert _parse(payload) is None


def test_parse_subagent_skill_captures_agent_id():
    event = _parse(_skill_payload(agent_id="ae8ec", agent_type="general-purpose"))
    assert event is not None and event.agent_id == "ae8ec"


def test_parse_runtime_comes_from_claude_config_dir(monkeypatch):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", "/Users/x/.claude-personal")
    event = _parse(_skill_payload())
    assert event is not None and event.runtime == ".claude-personal"


def test_parse_runtime_defaults_to_claude_without_env(monkeypatch):
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    event = _parse(_skill_payload())
    assert event is not None and event.runtime == "claude"


def test_parse_unknown_repo_falls_back_without_raising():
    event = _parse(_skill_payload())
    assert event is not None
    assert event.branch == "unknown"
    assert event.repo


def test_events_path_rotates_by_month(vague_home_dir, monkeypatch):
    monkeypatch.setenv("VAGUE_HOME", str(vague_home_dir))
    assert events_path(now=NOW) == vague_home_dir / "events" / "2026-11.jsonl"
    december = datetime(2026, 12, 1, tzinfo=UTC)
    assert events_path(now=december).name == "2026-12.jsonl"


def test_append_event_writes_one_json_line_and_creates_dirs(vague_home_dir, monkeypatch):
    monkeypatch.setenv("VAGUE_HOME", str(vague_home_dir))
    append_event(event=_event())
    lines = events_path(now=NOW).read_text().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["ts"].startswith("2026-11-11T10:00:00")
    assert "skill" not in row and "agent_id" not in row


def test_append_event_twice_appends_two_lines(vague_home_dir, monkeypatch):
    monkeypatch.setenv("VAGUE_HOME", str(vague_home_dir))
    append_event(event=_event())
    append_event(event=_event())
    assert len(events_path(now=NOW).read_text().splitlines()) == 2


def test_append_event_uses_event_month_for_file(vague_home_dir, monkeypatch):
    monkeypatch.setenv("VAGUE_HOME", str(vague_home_dir))
    append_event(event=_event(ts=datetime(2026, 12, 3, tzinfo=UTC)))
    assert (vague_home_dir / "events" / "2026-12.jsonl").exists()
