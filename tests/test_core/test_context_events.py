"""Tests for context_read / context_write events emitted by vague's own commands."""

from __future__ import annotations

import json
import shutil

import pytest
from typer.testing import CliRunner

import vague.sdk.core.events as events_module
from vague.sdk.cli import sdk_app
from vague.sdk.core.events import log_context_access

runner = CliRunner()

LOG = ["memory-log", "k", "TOPSECRETINSIGHT fact", "--global"]
SEARCH = ["memory-search", "TOPSECRETINSIGHT", "--scope", "all"]


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


def test_memory_log_records_context_write_with_command(home, in_session):
    result = runner.invoke(sdk_app, LOG)
    assert result.exit_code == 0
    (event,) = _context(home)
    assert event["event"] == "context_write"
    assert event["command"] == "memory-log"
    assert event["path"] == "memory.jsonl"
    assert event["session"] == "sess-1"


def test_memory_search_records_context_read(home, in_session, monkeypatch):
    runner.invoke(sdk_app, LOG)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-2")
    runner.invoke(sdk_app, SEARCH)
    reads = [e for e in _context(home) if e["session"] == "sess-2"]
    assert [(e["event"], e["command"]) for e in reads] == [("context_read", "memory-search")]
    assert reads[0]["path"] == "memory.jsonl"


def test_context_skill_records_ledger_read_and_no_writes(home, in_session):
    runner.invoke(sdk_app, LOG)
    runner.invoke(sdk_app, ["context", "--skill", "dev-ship"])
    rows = [(e["event"], e["path"].rsplit("/", 1)[-1]) for e in _context(home) if e["command"] == "context"]
    assert ("context_read", "memory.jsonl") in rows
    assert [r for r in rows if r[0] == "context_write"] == []


def test_scratch_write_records_relative_scratch_path(home, in_session):
    runner.invoke(sdk_app, ["memory-log", "note", "a note", "--global", "--scratch"])
    (event,) = _context(home)
    assert event["path"] == "scratch/global.jsonl"


def test_config_commands_record_their_file(home, in_session):
    runner.invoke(sdk_app, ["config-set", "proactive", "false"])
    runner.invoke(sdk_app, ["config-get", "proactive"])
    seen = {(e["command"], e["event"], e["path"].rsplit("/", 1)[1]) for e in _context(home)}
    assert ("config-set", "context_write", "config.md") in seen
    assert ("config-get", "context_read", "config.md") in seen


def test_session_id_unset_logs_unknown_session(home):
    result = runner.invoke(sdk_app, LOG)
    assert result.exit_code == 0
    (event,) = _context(home)
    assert event["session"] == "unknown"


def test_session_id_empty_logs_unknown_session(home, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "")
    runner.invoke(sdk_app, LOG)
    (event,) = _context(home)
    assert event["session"] == "unknown"


def test_ids_are_recorded_when_given(home, in_session, tmp_path):
    target = tmp_path / "memory.jsonl"
    target.write_text("x")
    events_module.begin_command(command="memory-search")
    log_context_access(kind="read", path=target, command="memory-search", ids=["o-r/k"])
    (event,) = _context(home)
    assert event["ids"] == ["o-r/k"]


def test_no_events_when_telemetry_off(home, in_session):
    runner.invoke(sdk_app, ["config-set", "telemetry", "off"])
    runner.invoke(sdk_app, LOG)
    runner.invoke(sdk_app, SEARCH)
    assert [e for e in _context(home) if e["command"].startswith("memory")] == []


def test_unwritable_events_dir_leaves_command_output_unchanged(home, in_session):
    runner.invoke(sdk_app, LOG)
    baseline = runner.invoke(sdk_app, SEARCH)
    shutil.rmtree(home / "events")
    (home / "events").write_text("a file where the directory should be")
    result = runner.invoke(sdk_app, SEARCH)
    assert result.exit_code == baseline.exit_code == 0
    assert result.stdout == baseline.stdout
    assert result.stderr == baseline.stderr


def test_path_is_normalized_through_symlinks(home, in_session, tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    (real / "memory.jsonl").write_text("x")
    link = tmp_path / "link"
    link.symlink_to(real)
    events_module.begin_command(command="memory-search")
    log_context_access(kind="read", path=link / "sub" / ".." / "memory.jsonl", command="memory-search")
    (event,) = _context(home)
    assert event["path"] == str((real / "memory.jsonl").resolve())


def test_contents_never_appear_in_event_lines(home, in_session):
    runner.invoke(sdk_app, LOG)
    runner.invoke(sdk_app, SEARCH)
    raw = "".join(f.read_text() for f in (home / "events").glob("*.jsonl"))
    assert "TOPSECRETINSIGHT" not in raw


def test_context_path_is_symlink_resolved(home, in_session, tmp_path):
    real = tmp_path / "real.md"
    real.write_text("x")
    link = tmp_path / "link.md"
    link.symlink_to(real)
    events_module.begin_command(command="config-get")
    log_context_access(kind="read", path=link, command="config-get")
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


def test_git_context_computed_once_for_command_touching_two_files(home, in_session, monkeypatch):
    runner.invoke(sdk_app, LOG)
    runner.invoke(sdk_app, ["config-set", "proactive", "true"])
    calls = []
    real = events_module.get_git_context

    def counting(*args, **kwargs):
        calls.append(1)
        return real(*args, **kwargs)

    monkeypatch.setattr(events_module, "get_git_context", counting)
    before = len(_context(home))
    runner.invoke(sdk_app, ["context", "--skill", "dev-ship"])
    assert len(_context(home)) - before >= 2
    assert len(calls) == 1


def test_status_logs_no_context_reads(home, in_session):
    runner.invoke(sdk_app, ["memory-log", "k", "a fact", "--global"])
    result = runner.invoke(sdk_app, ["status", "--json"])
    assert result.exit_code == 0
    assert [e for e in _context(home) if e["command"] == "status"] == []
