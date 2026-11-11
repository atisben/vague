"""Tests for `vague log-event`."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from vague.sdk.cli import sdk_app

runner = CliRunner()


@pytest.fixture
def home(vague_home_dir, monkeypatch):
    monkeypatch.setenv("VAGUE_HOME", str(vague_home_dir))
    return vague_home_dir


def _lines(home):
    files = list((home / "events").glob("*.jsonl")) if (home / "events").exists() else []
    return [json.loads(line) for f in files for line in f.read_text().splitlines()]


def _skill_payload(**extra):
    payload = {
        "hook_event_name": "PostToolUse", "tool_name": "Skill", "tool_input": {"skill": "learn"},
        "tool_response": {"success": True}, "session_id": "s1", "cwd": "/nonexistent/x",
    }
    payload.update(extra)
    return json.dumps(payload)


def test_log_event_skill_tool_records_skill_start(home):
    runner.invoke(sdk_app, ["log-event"], input=_skill_payload())
    (row,) = _lines(home)
    assert (row["event"], row["skill"], row["source"]) == ("skill_start", "learn", "tool")


def test_log_event_slash_prompt_stores_name_only(home):
    payload = {
        "hook_event_name": "UserPromptSubmit", "prompt": "/dev-ship TOPSECRETTEXT",
        "session_id": "s1", "cwd": "/nonexistent/x",
    }
    runner.invoke(sdk_app, ["log-event"], input=json.dumps(payload))
    raw = "".join(f.read_text() for f in (home / "events").glob("*.jsonl"))
    assert "TOPSECRETTEXT" not in raw
    assert json.loads(raw)["skill"] == "dev-ship"


SILENT = [
    {"hook_event_name": "PostToolUse", "tool_name": "Write",
     "tool_input": {"file_path": "/tmp/x.txt", "content": "SECRET"}, "tool_response": {"type": "create"}},
    {"hook_event_name": "PostToolUse", "tool_name": "Edit", "tool_input": {"file_path": "/tmp/x.txt"}},
    {"hook_event_name": "PostToolUse", "tool_name": "NotebookEdit", "tool_input": {"notebook_path": "/tmp/n.ipynb"}},
    {"hook_event_name": "PostToolUse", "tool_name": "Read", "tool_input": {"file_path": "/etc/hosts"},
     "tool_response": {"file": {"content": "BODY"}}},
    {"hook_event_name": "PostToolUse", "tool_name": "Grep", "tool_input": {"pattern": "PAT"},
     "tool_response": {"mode": "files_with_matches", "filenames": ["a.txt"]}},
    {"hook_event_name": "PostToolUse", "tool_name": "Glob", "tool_input": {"pattern": "*.txt"},
     "tool_response": {"filenames": ["a.txt"]}},
    {"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": "echo hi"}},
    {"hook_event_name": "SessionStart", "source": "startup"},
    {"hook_event_name": "Stop"},
    {"hook_event_name": "SessionEnd"},
    {"hook_event_name": "PostToolUseFailure", "tool_name": "Read", "tool_input": {"file_path": "/x"}},
]


@pytest.mark.parametrize("payload", SILENT, ids=[p.get("tool_name") or p["hook_event_name"] for p in SILENT])
def test_log_event_payload_unrelated_to_vague_usage_writes_nothing(home, payload):
    payload = {**payload, "session_id": "s1", "cwd": "/nonexistent/x"}
    result = runner.invoke(sdk_app, ["log-event"], input=json.dumps(payload))
    assert result.exit_code == 0
    assert result.stdout == ""
    assert _lines(home) == []


def test_log_event_telemetry_off_writes_nothing(home):
    (home / "config.md").write_text("---\ntelemetry: 'off'\n---\n")
    result = runner.invoke(sdk_app, ["log-event"], input=_skill_payload())
    assert result.exit_code == 0
    assert not (home / "events").exists()


@pytest.mark.parametrize("stdin", ["", "not json", "[1, 2]", "null"])
def test_log_event_bad_stdin_exits_zero_silently(home, stdin):
    result = runner.invoke(sdk_app, ["log-event"], input=stdin)
    assert result.exit_code == 0
    assert result.stdout == ""
    assert not (home / "events").exists()


def test_log_event_unwritable_home_exits_zero_silently(tmp_path, monkeypatch):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    monkeypatch.setenv("VAGUE_HOME", str(blocker))
    result = runner.invoke(sdk_app, ["log-event"], input=_skill_payload())
    assert result.exit_code == 0
    assert result.stdout == ""


def test_log_event_two_calls_append_two_lines(home):
    runner.invoke(sdk_app, ["log-event"], input=_skill_payload())
    runner.invoke(sdk_app, ["log-event"], input=_skill_payload())
    assert len(_lines(home)) == 2


def test_log_event_subagent_agent_id_is_captured(home):
    runner.invoke(sdk_app, ["log-event"], input=_skill_payload(agent_id="ae8ec", agent_type="general-purpose"))
    (row,) = _lines(home)
    assert row["agent_id"] == "ae8ec"


def test_log_event_runtime_from_claude_config_dir(home, monkeypatch):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", "/Users/x/.claude-personal")
    runner.invoke(sdk_app, ["log-event"], input=_skill_payload())
    (row,) = _lines(home)
    assert row["runtime"] == ".claude-personal"
