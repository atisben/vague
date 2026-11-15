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


def test_log_event_write_after_skill_logs_file_write(home, tmp_path):
    runner.invoke(sdk_app, ["log-event"], input=_skill_payload())
    write = {
        "hook_event_name": "PostToolUse", "tool_name": "Write", "session_id": "s1", "cwd": "/nonexistent/x",
        "tool_input": {"file_path": str(tmp_path / "a.txt"), "content": "SECRET"},
    }

    result = runner.invoke(sdk_app, ["log-event"], input=json.dumps(write))

    assert result.exit_code == 0
    skill_row, write_row = sorted(_lines(home), key=lambda r: r["event"] != "skill_start")
    assert (write_row["event"], write_row["skill"]) == ("file_write", "learn")
    assert "SECRET" not in json.dumps(write_row)


@pytest.fixture
def bundled_root(tmp_path, monkeypatch):
    """A tmp bundled skills root, so the hook checks test skills instead of the real ones."""
    root = tmp_path / "repo" / "vague" / "assets" / "skills"
    root.mkdir(parents=True)
    monkeypatch.setattr("vague.sdk.commands.events._bundled_skills_root", lambda: root.resolve())
    return root


def _edit(hook_payload, path):
    return json.dumps(hook_payload(tool_name="Edit", tool_input={"file_path": str(path)}))


def test_edit_of_invalid_skill_file_exits_2_with_findings(home, bundled_root, skill_dir, hook_payload):
    directory = skill_dir(name="broken", omit=("description",), root=bundled_root)

    result = runner.invoke(sdk_app, ["log-event"], input=_edit(hook_payload, directory / "SKILL.md"))

    assert result.exit_code == 2
    lines = result.stderr.splitlines()
    assert lines[0] == "vague skill-check: 1 finding(s) in broken"
    assert "missing required field `description`" in lines[1]
    assert result.stdout == ""


def test_edit_of_valid_skill_file_exits_0_silently(home, bundled_root, skill_dir, hook_payload):
    directory = skill_dir(name="fine", root=bundled_root)

    result = runner.invoke(sdk_app, ["log-event"], input=_edit(hook_payload, directory / "SKILL.md"))

    assert result.exit_code == 0
    assert result.stdout == ""
    assert result.stderr == ""


def test_edit_through_symlinked_skills_dir_is_checked(home, bundled_root, skill_dir, hook_payload, tmp_path):
    skill_dir(name="broken", omit=("version",), root=bundled_root)
    installed = tmp_path / "claude" / "skills"
    installed.mkdir(parents=True)
    (installed / "broken").symlink_to(bundled_root / "broken")

    result = runner.invoke(sdk_app, ["log-event"], input=_edit(hook_payload, installed / "broken" / "SKILL.md"))

    assert result.exit_code == 2
    assert "version" in result.stderr


def test_skill_md_outside_bundled_root_is_not_checked(home, bundled_root, skill_dir, hook_payload, tmp_path):
    directory = skill_dir(name="elsewhere", omit=("description",), root=tmp_path / "other")

    result = runner.invoke(sdk_app, ["log-event"], input=_edit(hook_payload, directory / "SKILL.md"))

    assert result.exit_code == 0
    assert result.stderr == ""


def test_check_failure_still_logs_event_and_exits_0(home, bundled_root, skill_dir, hook_payload, monkeypatch):
    directory = skill_dir(name="broken", omit=("description",), root=bundled_root)

    def _boom(skill_dir):
        raise RuntimeError("rule crashed")

    monkeypatch.setattr("vague.sdk.core.skill_rules.check_skill", _boom)
    runner.invoke(sdk_app, ["log-event"], input=_skill_payload())

    result = runner.invoke(sdk_app, ["log-event"], input=_edit(hook_payload, directory / "SKILL.md"))

    assert result.exit_code == 0
    assert result.stderr == ""
    assert [row["event"] for row in _lines(home)].count("file_write") == 1


def test_telemetry_off_skips_event_but_runs_check(home, bundled_root, skill_dir, hook_payload):
    (home / "config.md").write_text("---\ntelemetry: 'off'\n---\n")
    directory = skill_dir(name="broken", omit=("description",), root=bundled_root)

    result = runner.invoke(sdk_app, ["log-event"], input=_edit(hook_payload, directory / "SKILL.md"))

    assert result.exit_code == 2
    assert "description" in result.stderr
    assert not (home / "events").exists()
