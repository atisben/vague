"""Tests for vague/events.py."""

from __future__ import annotations

import json
import os
import shutil
from datetime import UTC, datetime

import pytest
from typer.testing import CliRunner

import vague.events as events_module
from vague.cli import app
from vague.events import Event, append_event, events_path, log_context_access, parse_hook_payload

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


def test_events_path_rotates_by_month(vague_home, monkeypatch):
    assert events_path(now=NOW) == vague_home / "events" / "2026-11.jsonl"
    december = datetime(2026, 12, 1, tzinfo=UTC)
    assert events_path(now=december).name == "2026-12.jsonl"


def test_append_event_writes_one_json_line_and_creates_dirs(vague_home, monkeypatch):
    append_event(event=_event())
    lines = events_path(now=NOW).read_text().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["ts"].startswith("2026-11-11T10:00:00")
    assert "skill" not in row and "agent_id" not in row


def test_append_event_twice_appends_two_lines(vague_home, monkeypatch):
    append_event(event=_event())
    append_event(event=_event())
    assert len(events_path(now=NOW).read_text().splitlines()) == 2


def test_append_event_uses_event_month_for_file(vague_home, monkeypatch):
    append_event(event=_event(ts=datetime(2026, 12, 3, tzinfo=UTC)))
    assert (vague_home / "events" / "2026-12.jsonl").exists()


@pytest.fixture
def events_home(vague_home, monkeypatch):
    return vague_home


def test_write_after_skill_start_yields_file_write_with_skill(events_home, hook_payload, tmp_path):
    append_event(event=_event(skill="plan-eng"))
    append_event(event=_event(skill="dev-ship"))
    append_event(event=_event(session="other", skill="vault"))
    target = tmp_path / "a.txt"

    event = _parse(hook_payload(tool_name="Write", tool_input={"file_path": str(target), "content": "SECRET"}))

    assert event is not None
    assert (event.event, event.skill) == ("file_write", "dev-ship")
    # tmp_path sits under /var on macOS, which resolves to /private/var.
    assert event.path == os.path.realpath(target)
    assert "SECRET" not in event.model_dump_json()


def test_edit_relative_path_resolves_against_cwd(events_home, hook_payload, tmp_path):
    append_event(event=_event(skill="dev-ship"))

    event = _parse(hook_payload(tool_name="Edit", tool_input={"file_path": "src/a.py"}, cwd=str(tmp_path)))

    assert event is not None and event.path == os.path.realpath(tmp_path / "src" / "a.py")


def test_write_without_skill_start_yields_no_event(events_home, hook_payload):
    append_event(event=_event(session="other", skill="dev-ship"))

    assert _parse(hook_payload(tool_name="Write", tool_input={"file_path": "/work/a.txt"})) is None


def test_read_tool_yields_no_event(events_home, hook_payload):
    append_event(event=_event(skill="dev-ship"))

    assert _parse(hook_payload(tool_name="Read", tool_input={"file_path": "/work/a.txt"})) is None


@pytest.mark.parametrize("tool_input", [None, {}, {"file_path": ""}, "not a dict"])
def test_write_without_file_path_yields_no_event(events_home, hook_payload, tool_input):
    append_event(event=_event(skill="dev-ship"))
    payload = hook_payload(tool_name="Write")
    payload["tool_input"] = tool_input

    assert _parse(payload) is None


runner = CliRunner()


LOG = ["memory-log", "k", "TOPSECRETINSIGHT fact", "--global"]


SEARCH = ["memory-search", "TOPSECRETINSIGHT", "--scope", "all"]


@pytest.fixture
def work_home(vague_home, monkeypatch, tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    return vague_home


@pytest.fixture
def in_session(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-1")


def _lines(work_home):
    events_dir = work_home / "events"
    files = list(events_dir.glob("*.jsonl")) if events_dir.is_dir() else []
    return [json.loads(line) for f in files for line in f.read_text().splitlines()]


def _context(work_home):
    return [e for e in _lines(work_home) if e["event"].startswith("context_")]


def test_memory_log_records_context_write_with_command(work_home, in_session):
    result = runner.invoke(app, LOG)
    assert result.exit_code == 0
    (event,) = _context(work_home)
    assert event["event"] == "context_write"
    assert event["command"] == "memory-log"
    assert event["path"] == "memory.jsonl"
    assert event["session"] == "sess-1"


def test_memory_search_records_context_read(work_home, in_session, monkeypatch):
    runner.invoke(app, LOG)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-2")
    runner.invoke(app, SEARCH)
    reads = [e for e in _context(work_home) if e["session"] == "sess-2"]
    assert [(e["event"], e["command"]) for e in reads] == [("context_read", "memory-search")]
    assert reads[0]["path"] == "memory.jsonl"


def test_context_skill_records_ledger_read_and_no_writes(work_home, in_session):
    runner.invoke(app, LOG)
    runner.invoke(app, ["context", "--skill", "dev-ship"])
    rows = [(e["event"], e["path"].rsplit("/", 1)[-1]) for e in _context(work_home) if e["command"] == "context"]
    assert ("context_read", "memory.jsonl") in rows
    assert [r for r in rows if r[0] == "context_write"] == []


def test_note_write_records_the_ledger_path(work_home, in_session):
    runner.invoke(app, ["memory-log", "note", "a note", "--global", "--scratch"])
    (event,) = _context(work_home)
    assert event["path"] == "memory.jsonl"


def test_config_commands_record_their_file(work_home, in_session):
    runner.invoke(app, ["config-set", "telemetry", "local"])
    runner.invoke(app, ["config-get", "telemetry"])
    seen = {(e["command"], e["event"], e["path"].rsplit("/", 1)[1]) for e in _context(work_home)}
    assert ("config-set", "context_write", "config.env") in seen
    assert ("config-get", "context_read", "config.env") in seen


def test_session_id_unset_logs_unknown_session(work_home):
    result = runner.invoke(app, LOG)
    assert result.exit_code == 0
    (event,) = _context(work_home)
    assert event["session"] == "unknown"


def test_session_id_empty_logs_unknown_session(work_home, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "")
    runner.invoke(app, LOG)
    (event,) = _context(work_home)
    assert event["session"] == "unknown"


def test_ids_are_recorded_when_given(work_home, in_session, tmp_path):
    target = tmp_path / "memory.jsonl"
    target.write_text("x")
    events_module.begin_command(command="memory-search")
    log_context_access(kind="read", path=target, command="memory-search", ids=["o-r/k"])
    (event,) = _context(work_home)
    assert event["ids"] == ["o-r/k"]


def test_no_events_when_telemetry_off(work_home, in_session):
    runner.invoke(app, ["config-set", "telemetry", "off"])
    runner.invoke(app, LOG)
    runner.invoke(app, SEARCH)
    assert [e for e in _context(work_home) if e["command"].startswith("memory")] == []


def test_unwritable_events_dir_leaves_command_output_unchanged(work_home, in_session):
    runner.invoke(app, LOG)
    baseline = runner.invoke(app, SEARCH)
    shutil.rmtree(work_home / "events")
    (work_home / "events").write_text("a file where the directory should be")
    result = runner.invoke(app, SEARCH)
    assert result.exit_code == baseline.exit_code == 0
    assert result.stdout == baseline.stdout
    assert result.stderr == baseline.stderr


def test_path_is_normalized_through_symlinks(work_home, in_session, tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    (real / "memory.jsonl").write_text("x")
    link = tmp_path / "link"
    link.symlink_to(real)
    events_module.begin_command(command="memory-search")
    log_context_access(kind="read", path=link / "sub" / ".." / "memory.jsonl", command="memory-search")
    (event,) = _context(work_home)
    assert event["path"] == str((real / "memory.jsonl").resolve())


def test_contents_never_appear_in_event_lines(work_home, in_session):
    runner.invoke(app, LOG)
    runner.invoke(app, SEARCH)
    raw = "".join(f.read_text() for f in (work_home / "events").glob("*.jsonl"))
    assert "TOPSECRETINSIGHT" not in raw


def test_context_path_is_symlink_resolved(work_home, in_session, tmp_path):
    real = tmp_path / "real.md"
    real.write_text("x")
    link = tmp_path / "link.md"
    link.symlink_to(real)
    events_module.begin_command(command="config-get")
    log_context_access(kind="read", path=link, command="config-get")
    (row,) = _context(work_home)
    assert row["path"] == str(real.resolve())


def test_log_event_itself_logs_no_context_events(work_home, in_session):
    (work_home / "config.env").write_text("telemetry=local\n")
    payload = {
        "hook_event_name": "PostToolUse", "tool_name": "Skill", "tool_input": {"skill": "learn"},
        "tool_response": {"success": True}, "session_id": "s1", "cwd": "/nonexistent/x",
    }
    result = runner.invoke(app, ["log-event"], input=json.dumps(payload))
    assert result.exit_code == 0
    assert _context(work_home) == []
    assert [e["event"] for e in _lines(work_home)] == ["skill_start"]


def test_git_context_computed_once_for_command_touching_two_files(work_home, in_session, monkeypatch):
    runner.invoke(app, LOG)
    runner.invoke(app, ["config-set", "telemetry", "local"])
    calls = []
    real = events_module.get_git_context

    def counting(*args, **kwargs):
        calls.append(1)
        return real(*args, **kwargs)

    monkeypatch.setattr(events_module, "get_git_context", counting)
    before = len(_context(work_home))
    runner.invoke(app, ["context", "--skill", "dev-ship"])
    assert len(_context(work_home)) - before >= 2
    assert len(calls) == 1


def test_status_logs_no_context_reads(work_home, in_session):
    runner.invoke(app, ["memory-log", "k", "a fact", "--global"])
    result = runner.invoke(app, ["status", "--json"])
    assert result.exit_code == 0
    assert [e for e in _context(work_home) if e["command"] == "status"] == []


def _lines(vague_home):
    files = list((vague_home / "events").glob("*.jsonl")) if (vague_home / "events").exists() else []
    return [json.loads(line) for f in files for line in f.read_text().splitlines()]


def _skill_payload_json(**extra):
    payload = {
        "hook_event_name": "PostToolUse", "tool_name": "Skill", "tool_input": {"skill": "learn"},
        "tool_response": {"success": True}, "session_id": "s1", "cwd": "/nonexistent/x",
    }
    payload.update(extra)
    return json.dumps(payload)


def test_log_event_skill_tool_records_skill_start(vague_home):
    runner.invoke(app, ["log-event"], input=_skill_payload_json())
    (row,) = _lines(vague_home)
    assert (row["event"], row["skill"], row["source"]) == ("skill_start", "learn", "tool")


def test_log_event_slash_prompt_stores_name_only(vague_home):
    payload = {
        "hook_event_name": "UserPromptSubmit", "prompt": "/dev-ship TOPSECRETTEXT",
        "session_id": "s1", "cwd": "/nonexistent/x",
    }
    runner.invoke(app, ["log-event"], input=json.dumps(payload))
    raw = "".join(f.read_text() for f in (vague_home / "events").glob("*.jsonl"))
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
def test_log_event_payload_unrelated_to_vague_usage_writes_nothing(vague_home, payload):
    payload = {**payload, "session_id": "s1", "cwd": "/nonexistent/x"}
    result = runner.invoke(app, ["log-event"], input=json.dumps(payload))
    assert result.exit_code == 0
    assert result.stdout == ""
    assert _lines(vague_home) == []


def test_log_event_telemetry_off_writes_nothing(vague_home):
    (vague_home / "config.env").write_text("telemetry=off\n")
    result = runner.invoke(app, ["log-event"], input=_skill_payload_json())
    assert result.exit_code == 0
    assert not (vague_home / "events").exists()


@pytest.mark.parametrize("stdin", ["", "not json", "[1, 2]", "null"])
def test_log_event_bad_stdin_exits_zero_silently(vague_home, stdin):
    result = runner.invoke(app, ["log-event"], input=stdin)
    assert result.exit_code == 0
    assert result.stdout == ""
    assert not (vague_home / "events").exists()


def test_log_event_unwritable_home_exits_zero_silently(tmp_path, monkeypatch):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    monkeypatch.setenv("VAGUE_HOME", str(blocker))
    result = runner.invoke(app, ["log-event"], input=_skill_payload_json())
    assert result.exit_code == 0
    assert result.stdout == ""


def test_log_event_two_calls_append_two_lines(vague_home):
    runner.invoke(app, ["log-event"], input=_skill_payload_json())
    runner.invoke(app, ["log-event"], input=_skill_payload_json())
    assert len(_lines(vague_home)) == 2


def test_log_event_subagent_agent_id_is_captured(vague_home):
    runner.invoke(app, ["log-event"], input=_skill_payload_json(agent_id="ae8ec", agent_type="general-purpose"))
    (row,) = _lines(vague_home)
    assert row["agent_id"] == "ae8ec"


def test_log_event_runtime_from_claude_config_dir(vague_home, monkeypatch):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", "/Users/x/.claude-personal")
    runner.invoke(app, ["log-event"], input=_skill_payload_json())
    (row,) = _lines(vague_home)
    assert row["runtime"] == ".claude-personal"


def test_log_event_write_after_skill_logs_file_write(vague_home, tmp_path):
    runner.invoke(app, ["log-event"], input=_skill_payload_json())
    write = {
        "hook_event_name": "PostToolUse", "tool_name": "Write", "session_id": "s1", "cwd": "/nonexistent/x",
        "tool_input": {"file_path": str(tmp_path / "a.txt"), "content": "SECRET"},
    }

    result = runner.invoke(app, ["log-event"], input=json.dumps(write))

    assert result.exit_code == 0
    skill_row, write_row = sorted(_lines(vague_home), key=lambda r: r["event"] != "skill_start")
    assert (write_row["event"], write_row["skill"]) == ("file_write", "learn")
    assert "SECRET" not in json.dumps(write_row)


@pytest.fixture
def bundled_root(tmp_path, monkeypatch):
    """A tmp bundled skills root, so the hook checks test skills instead of the real ones."""
    root = tmp_path / "repo" / "vague" / "assets" / "skills"
    root.mkdir(parents=True)
    monkeypatch.setattr("vague.events._bundled_skills_root", lambda: root.resolve())
    return root


def _edit(hook_payload, path):
    return json.dumps(hook_payload(tool_name="Edit", tool_input={"file_path": str(path)}))


def test_edit_of_invalid_skill_file_exits_2_with_findings(vague_home, bundled_root, skill_dir, hook_payload):
    directory = skill_dir(name="broken", omit=("description",), root=bundled_root)

    result = runner.invoke(app, ["log-event"], input=_edit(hook_payload, directory / "SKILL.md"))

    assert result.exit_code == 2
    lines = result.stderr.splitlines()
    assert lines[0] == "vague skill-check: 1 finding(s) in broken"
    assert "missing required field `description`" in lines[1]
    assert result.stdout == ""


def test_edit_of_valid_skill_file_exits_0_silently(vague_home, bundled_root, skill_dir, hook_payload):
    directory = skill_dir(name="fine", root=bundled_root)

    result = runner.invoke(app, ["log-event"], input=_edit(hook_payload, directory / "SKILL.md"))

    assert result.exit_code == 0
    assert result.stdout == ""
    assert result.stderr == ""


def test_edit_through_symlinked_skills_dir_is_checked(vague_home, bundled_root, skill_dir, hook_payload, tmp_path):
    skill_dir(name="broken", omit=("version",), root=bundled_root)
    installed = tmp_path / "claude" / "skills"
    installed.mkdir(parents=True)
    (installed / "broken").symlink_to(bundled_root / "broken")

    result = runner.invoke(app, ["log-event"], input=_edit(hook_payload, installed / "broken" / "SKILL.md"))

    assert result.exit_code == 2
    assert "version" in result.stderr


def test_skill_md_outside_bundled_root_is_not_checked(vague_home, bundled_root, skill_dir, hook_payload, tmp_path):
    directory = skill_dir(name="elsewhere", omit=("description",), root=tmp_path / "other")

    result = runner.invoke(app, ["log-event"], input=_edit(hook_payload, directory / "SKILL.md"))

    assert result.exit_code == 0
    assert result.stderr == ""


def test_check_failure_still_logs_event_and_exits_0(vague_home, bundled_root, skill_dir, hook_payload, monkeypatch):
    directory = skill_dir(name="broken", omit=("description",), root=bundled_root)

    def _boom(skill_dir):
        raise RuntimeError("rule crashed")

    monkeypatch.setattr("vague.skill_rules.check_skill", _boom)
    runner.invoke(app, ["log-event"], input=_skill_payload_json())

    result = runner.invoke(app, ["log-event"], input=_edit(hook_payload, directory / "SKILL.md"))

    assert result.exit_code == 0
    assert result.stderr == ""
    assert [row["event"] for row in _lines(vague_home)].count("file_write") == 1


def test_telemetry_off_skips_event_but_runs_check(vague_home, bundled_root, skill_dir, hook_payload):
    (vague_home / "config.env").write_text("telemetry=off\n")
    directory = skill_dir(name="broken", omit=("description",), root=bundled_root)

    result = runner.invoke(app, ["log-event"], input=_edit(hook_payload, directory / "SKILL.md"))

    assert result.exit_code == 2
    assert "description" in result.stderr
    assert not (vague_home / "events").exists()
