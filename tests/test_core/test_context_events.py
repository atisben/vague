"""Tests for context_read / context_write events emitted by vague's own commands."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

import vague.sdk.core.events as events_module
from vague.sdk.cli import sdk_app
from vague.sdk.core.events import log_context_access

runner = CliRunner()

LEARNING = json.dumps({
    "skill": "test", "type": "pitfall", "key": "k", "insight": "TOPSECRETINSIGHT",
    "confidence": 7, "source": "observed", "ts": "2024-01-01T00:00:00+00:00",
})


@pytest.fixture
def home(vague_home_dir, monkeypatch, tmp_path):
    monkeypatch.setenv("VAGUE_HOME", str(vague_home_dir))
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    return vague_home_dir


@pytest.fixture
def in_session(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-1")


def _lines(home):
    events_dir = home / "events"
    files = list(events_dir.glob("*.jsonl")) if events_dir.is_dir() else []
    return [json.loads(line) for f in files for line in f.read_text().splitlines()]


def _context(home):
    return [e for e in _lines(home) if e["event"].startswith("context_")]


def test_learnings_log_records_context_write_with_command(home, in_session):
    result = runner.invoke(sdk_app, ["learnings-log", LEARNING])
    assert result.exit_code == 0
    (event,) = _context(home)
    assert event["event"] == "context_write"
    assert event["command"] == "learnings-log"
    assert event["path"].endswith("/learnings.md")
    assert event["session"] == "sess-1"


def test_learnings_search_records_context_read(home, in_session, monkeypatch):
    runner.invoke(sdk_app, ["learnings-log", LEARNING])
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-2")
    runner.invoke(sdk_app, ["learnings-search"])
    reads = [e for e in _context(home) if e["session"] == "sess-2"]
    assert [(e["event"], e["command"]) for e in reads] == [("context_read", "learnings-search")]
    assert reads[0]["path"].endswith("/learnings.md")


def test_context_skill_records_learnings_read_and_project_write(home, in_session):
    runner.invoke(sdk_app, ["learnings-log", LEARNING])
    runner.invoke(sdk_app, ["context", "--skill", "dev-ship"])
    rows = [(e["event"], e["path"].rsplit("/", 1)[1]) for e in _context(home) if e["command"] == "context"]
    assert ("context_read", "learnings.md") in rows
    assert ("context_write", "project.md") in rows


def test_other_state_commands_record_their_files(home, in_session):
    runner.invoke(sdk_app, ["timeline-log", json.dumps({"skill": "x", "event": "started"})])
    runner.invoke(sdk_app, ["config-set", "proactive", "false"])
    runner.invoke(sdk_app, ["config-get", "proactive"])
    runner.invoke(sdk_app, ["state-set", "phase", "1"])
    runner.invoke(sdk_app, ["state-get", "phase"])
    seen = {(e["command"], e["event"], e["path"].rsplit("/", 1)[1]) for e in _context(home)}
    assert ("timeline-log", "context_write", "timeline.md") in seen
    assert ("config-set", "context_write", "config.md") in seen
    assert ("config-get", "context_read", "config.md") in seen
    assert ("state-set", "context_write", "state.md") in seen
    assert ("state-get", "context_read", "state.md") in seen


def test_no_events_file_when_session_id_unset(home):
    result = runner.invoke(sdk_app, ["learnings-log", LEARNING])
    assert result.exit_code == 0
    assert not (home / "events").exists()


def test_no_events_file_when_session_id_empty(home, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "")
    runner.invoke(sdk_app, ["learnings-log", LEARNING])
    assert not (home / "events").exists()


def test_no_events_when_telemetry_off(home, in_session):
    runner.invoke(sdk_app, ["config-set", "telemetry", "off"])
    runner.invoke(sdk_app, ["learnings-log", LEARNING])
    runner.invoke(sdk_app, ["learnings-search"])
    assert [e for e in _context(home) if e["command"].startswith("learnings")] == []


def test_unwritable_events_dir_leaves_command_output_unchanged(home, in_session):
    baseline = runner.invoke(sdk_app, ["learnings-search"])
    (home / "events").write_text("a file where the directory should be")
    result = runner.invoke(sdk_app, ["learnings-search"])
    assert result.exit_code == baseline.exit_code == 0
    assert result.stdout == baseline.stdout
    assert result.stderr == baseline.stderr


def test_path_is_normalized_through_symlinks(home, in_session, tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    (real / "learnings.md").write_text("x")
    link = tmp_path / "link"
    link.symlink_to(real)
    events_module.begin_command(command="learnings-search")
    log_context_access(kind="read", path=link / "sub" / ".." / "learnings.md", command="learnings-search")
    (event,) = _context(home)
    assert event["path"] == str((real / "learnings.md").resolve())


def test_contents_never_appear_in_event_lines(home, in_session):
    runner.invoke(sdk_app, ["learnings-log", LEARNING])
    runner.invoke(sdk_app, ["learnings-search"])
    raw = "".join(f.read_text() for f in (home / "events").glob("*.jsonl"))
    assert "TOPSECRETINSIGHT" not in raw


def test_context_path_is_symlink_resolved(home, in_session, tmp_path):
    real = tmp_path / "real.md"
    real.write_text("x")
    link = tmp_path / "link.md"
    link.symlink_to(real)
    events_module.begin_command(command="state-get")
    log_context_access(kind="read", path=link, command="state-get")
    (row,) = _context(home)
    assert row["path"] == str(real.resolve())


def test_log_event_itself_logs_no_context_events(home, in_session):
    (home / "config.md").write_text("---\nproactive: true\n---\n")
    payload = {
        "hook_event_name": "PostToolUse", "tool_name": "Skill", "tool_input": {"skill": "learn"},
        "tool_response": {"success": True}, "session_id": "s1", "cwd": "/nonexistent/x",
    }
    result = runner.invoke(sdk_app, ["log-event"], input=json.dumps(payload))
    assert result.exit_code == 0
    assert _context(home) == []
    assert [e["event"] for e in _lines(home)] == ["skill_start"]


def test_git_context_computed_once_for_command_touching_three_files(home, in_session, monkeypatch):
    runner.invoke(sdk_app, ["learnings-log", LEARNING])
    runner.invoke(sdk_app, ["config-set", "proactive", "true"])
    calls = []
    real = events_module.get_git_context

    def counting(*args, **kwargs):
        calls.append(1)
        return real(*args, **kwargs)

    monkeypatch.setattr(events_module, "get_git_context", counting)
    before = len(_context(home))
    runner.invoke(sdk_app, ["context", "--skill", "dev-ship"])
    assert len(_context(home)) - before >= 3
    assert len(calls) == 1


def test_status_logs_at_most_the_read_cap(home, in_session, monkeypatch):
    monkeypatch.setattr(events_module, "MAX_STATUS_READS", 4)
    for i in range(5):
        project = home / "projects" / f"p{i}"
        project.mkdir(parents=True)
        (project / "project.md").write_text("---\npath: /nonexistent\n---\n")
        (project / "learnings.md").write_text("---\nentries: []\n---\n")
    result = runner.invoke(sdk_app, ["status", "--json"])
    assert result.exit_code == 0
    assert len([e for e in _context(home) if e["command"] == "status"]) == 4
