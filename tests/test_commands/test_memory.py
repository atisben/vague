"""Tests for the memory-log and memory-search commands, and the memory block in the preamble."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from vague.sdk.cli import sdk_app
from vague.sdk.core.memory import BLOCK_LIMIT, Memory, append_memory, ledger_path, scratch_path

runner = CliRunner()


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=cwd, check=True,
                   capture_output=True)


@pytest.fixture
def home():
    return Path(os.environ["VAGUE_HOME"])


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A repo with an origin remote, so the scope is the stable slug `o-r`."""
    path = tmp_path / "r"
    path.mkdir()
    _git(path, "init", "-b", "main")
    _git(path, "remote", "add", "origin", "https://github.com/o/r.git")
    (path / "Taskfile.yml").write_text("version: 3\n")
    _git(path, "add", ".")
    _git(path, "commit", "-m", "init")
    monkeypatch.chdir(path)
    return path


@pytest.fixture
def in_session(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-1")


def _ledger(home: Path) -> list[dict]:
    path = home / "memory.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def _events(home: Path) -> list[dict]:
    events_dir = home / "events"
    files = sorted(events_dir.glob("*.jsonl")) if events_dir.is_dir() else []
    return [json.loads(line) for f in files for line in f.read_text().splitlines()]


def _log(*args: str):
    return runner.invoke(sdk_app, ["memory-log", *args])


def test_memory_log_appends_one_parseable_line(home, repo):
    result = _log("tests-need-docker", "Run task tests.", "--files", "Taskfile.yml, src/a.py")
    assert result.exit_code == 0, result.output
    assert result.stdout.strip() == "OK o-r/tests-need-docker"
    (row,) = _ledger(home)
    assert (row["scope"], row["key"], row["kind"], row["text"]) == ("o-r", "tests-need-docker", "learning",
                                                                    "Run task tests.")
    assert row["files"] == ["Taskfile.yml", "src/a.py"]
    assert row["status"] == "active"


def test_memory_log_global_writes_global_scope(home, repo):
    assert _log("verify-subagents", "Check the seams yourself.", "--global").exit_code == 0
    assert _ledger(home)[0]["scope"] == "global"


def test_memory_log_in_home_without_global_exits_1_and_writes_nothing(home, tmp_path, monkeypatch):
    fake_home = tmp_path / "me"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.chdir(fake_home)
    result = _log("k", "text")
    assert result.exit_code == 1
    assert "--global" in result.stderr
    assert not (home / "memory.jsonl").exists()
    assert _log("k", "text", "--global").exit_code == 0


def test_memory_log_about_writes_global_observation(home, repo):
    assert _log("ship-skips-tests", "dev-ship skipped the suite.", "--about", "dev-ship").exit_code == 0
    (row,) = _ledger(home)
    assert (row["scope"], row["kind"], row["skill"]) == ("global", "observation", "dev-ship")


def test_memory_log_without_text_or_status_errors(home, repo):
    result = _log("k")
    assert result.exit_code == 1
    assert not (home / "memory.jsonl").exists()


def test_memory_log_text_over_600_chars_errors(home, repo):
    result = _log("k", "x" * 601)
    assert result.exit_code == 1
    assert "600" in result.stderr
    assert not (home / "memory.jsonl").exists()


def test_memory_log_bad_status_errors(home, repo):
    assert _log("k", "--status", "deleted").exit_code == 1


def test_memory_log_status_only_forgets_and_keeps_history(home, repo):
    _log("k", "SECRETFACT")
    result = _log("k", "--status", "forgotten")
    assert result.exit_code == 0
    rows = _ledger(home)
    assert len(rows) == 2 and "text" not in rows[1] and rows[1]["status"] == "forgotten"
    assert "SECRETFACT" not in runner.invoke(sdk_app, ["memory-search", "secretfact"]).stdout
    assert "SECRETFACT" not in runner.invoke(sdk_app, ["context", "--shell", "--skill", "x"]).stdout


def test_memory_log_status_only_keeps_observation_kind(home, repo):
    _log("obs", "an observation", "--about", "meta")
    assert _log("obs", "--status", "actioned", "--global").exit_code == 0
    assert _ledger(home)[1]["kind"] == "observation"


def test_memory_log_status_only_observation_falls_back_to_global_scope(home, repo):
    _log("obs", "an observation", "--about", "meta")
    result = _log("obs", "--status", "actioned")
    assert result.exit_code == 0, result.output
    assert result.stdout.strip() == "OK global/obs"
    row = _ledger(home)[1]
    assert (row["scope"], row["kind"], row["status"]) == ("global", "observation", "actioned")


def test_memory_log_status_only_prefers_current_scope_over_global(home, repo):
    _log("k", "project fact")
    _log("k", "global fact", "--global")
    assert _log("k", "--status", "forgotten").stdout.strip() == "OK o-r/k"


def test_memory_log_status_only_for_unknown_key_errors(home, repo):
    assert _log("never-logged", "--status", "forgotten").exit_code == 1
    assert not (home / "memory.jsonl").exists()


def test_memory_log_scratch_writes_scratch_file_not_ledger(home, repo):
    result = _log("claim-auth-refactor", "agent 2 owns src/auth", "--scratch")
    assert result.exit_code == 0
    assert not (home / "memory.jsonl").exists()
    (line,) = scratch_path(scope="o-r").read_text().splitlines()
    assert json.loads(line)["key"] == "claim-auth-refactor"


def test_memory_search_ands_words_and_logs_served_ids(home, repo, in_session):
    _log("tests-need-docker", "Run task tests in docker.", "--files", "Taskfile.yml")
    _log("docker-other", "Unrelated docker fact.")
    _log("elsewhere", "docker but not the other word", "--global")
    result = runner.invoke(sdk_app, ["memory-search", "docker", "taskfile"])
    assert result.exit_code == 0
    assert result.stdout.splitlines() == ["o-r/tests-need-docker  Run task tests in docker.  (files: Taskfile.yml)"]
    (read,) = [e for e in _events(home) if e["command"] == "memory-search"]
    assert read["event"] == "context_read"
    assert read["ids"] == ["o-r/tests-need-docker"]


def test_memory_search_kind_observation_searches_global(home, repo):
    _log("obs", "skill feedback here", "--about", "meta")
    _log("learn", "skill feedback here")
    result = runner.invoke(sdk_app, ["memory-search", "feedback", "--kind", "observation"])
    assert result.stdout.splitlines() == ["global/obs  [meta]  skill feedback here"]


def test_memory_search_prints_skill_and_matches_it(home, repo):
    _log("obs-a", "slow step", "--about", "dev-ship")
    _log("obs-b", "slow step", "--about", "retro")
    result = runner.invoke(sdk_app, ["memory-search", "dev-ship", "--kind", "observation"])
    assert result.stdout.splitlines() == ["global/obs-a  [dev-ship]  slow step"]


def test_memory_search_prints_files_when_set(home, repo):
    _log("tests-need-docker", "tests run in the container", "--files", "Taskfile.yml,compose.yml")
    _log("no-files", "plain fact")
    result = runner.invoke(sdk_app, ["memory-search"])
    lines = sorted(line.split("/", 1)[1] for line in result.stdout.splitlines())
    assert lines == ["no-files  plain fact",
                     "tests-need-docker  tests run in the container  (files: Taskfile.yml, compose.yml)"]


def test_context_help_says_skill_ranks_memory_block():
    result = runner.invoke(sdk_app, ["context", "--help"], terminal_width=200)
    assert "Rank the memory block" in " ".join(result.stdout.split())


def test_status_help_mentions_designs_not_plans():
    result = runner.invoke(sdk_app, ["status", "--help"], terminal_width=200)
    assert "in-flight designs" in result.stdout and "plans" not in result.stdout


def _put(scope: str, key: str, text: str = "needle", minutes_ago: int = 0, scratch: bool = False) -> None:
    ts = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    append_memory(memory=Memory(ts=ts, scope=scope, key=key, kind="learning", text=text), scratch=scratch)


def _search(*args: str) -> list[str]:
    return runner.invoke(sdk_app, ["memory-search", *args]).stdout.splitlines()


def test_memory_search_default_covers_current_scope_and_global_only(home, repo):
    _put(scope="o-r", key="here")
    _put(scope="global", key="g")
    _put(scope="elsewhere", key="k")
    assert sorted(_search("needle")) == ["global/g  needle", "o-r/here  needle"]


def test_memory_search_scope_global_returns_only_global(home, repo):
    _put(scope="o-r", key="here")
    _put(scope="global", key="g")
    assert _search("needle", "--scope", "global") == ["global/g  needle"]


def test_memory_search_scope_project_returns_only_that_project(home, repo):
    _put(scope="o-r", key="here")
    _put(scope="global", key="g")
    _put(scope="elsewhere", key="k")
    assert _search("needle", "--scope", "elsewhere") == ["elsewhere/k  needle"]


def test_memory_search_scope_all_spans_every_scope(home, repo):
    _put(scope="o-r", key="here", minutes_ago=2)
    _put(scope="global", key="g", minutes_ago=1)
    _put(scope="elsewhere", key="k")
    assert _search("needle", "--scope", "all") == ["elsewhere/k  needle", "global/g  needle", "o-r/here  needle"]


def test_memory_search_scope_unknown_says_no_match(home, repo):
    _put(scope="o-r", key="here")
    result = runner.invoke(sdk_app, ["memory-search", "--scope", "nope"])
    assert result.exit_code == 0
    assert result.stdout.strip() == "No memories match."


def test_memory_search_without_words_lists_every_active_memory_newest_first(home, repo, in_session):
    _put(scope="elsewhere", key="old", text="first", minutes_ago=3)
    _put(scope="global", key="mid", text="second", minutes_ago=2)
    _put(scope="other", key="new", text="third", minutes_ago=1)
    _log("gone", "forgotten fact")
    _log("gone", "--status", "forgotten")
    assert _search("--scope", "all") == ["other/new  third", "global/mid  second", "elsewhere/old  first"]
    (read,) = [e for e in _events(home) if e["command"] == "memory-search"]
    assert read["ids"] == ["other/new", "global/mid", "elsewhere/old"]


def test_memory_search_scope_all_scratch_spans_every_scratchpad(home, repo):
    _put(scope="o-r", key="mine", scratch=True, minutes_ago=1)
    _put(scope="elsewhere", key="theirs", scratch=True)
    assert _search("--scratch") == ["o-r/mine  needle"]
    assert _search("--scratch", "--scope", "all") == ["elsewhere/theirs  needle", "o-r/mine  needle"]
    assert _search("--scratch", "--scope", "elsewhere") == ["elsewhere/theirs  needle"]


def test_memory_search_old_all_flag_is_rejected(home, repo):
    assert runner.invoke(sdk_app, ["memory-search", "needle", "--all"]).exit_code == 2


def test_memory_review_command_is_gone(home, repo):
    assert runner.invoke(sdk_app, ["memory-review"]).exit_code == 2


def test_memory_search_scratch_hides_old_notes(home, repo):
    old = datetime.now(UTC) - timedelta(days=8)
    append_memory(memory=Memory(ts=old, scope="o-r", key="old", kind="learning", text="needle"), scratch=True)
    _log("fresh", "needle", "--scratch")
    result = runner.invoke(sdk_app, ["memory-search", "needle", "--scratch"])
    assert result.stdout.splitlines() == ["o-r/fresh  needle"]


def test_memory_log_logs_context_write_with_id(home, repo, in_session):
    _log("k", "text")
    (write,) = [e for e in _events(home) if e["command"] == "memory-log"]
    assert write["event"] == "context_write"
    assert write["ids"] == ["o-r/k"]
    assert write["path"] == "memory.jsonl"


def test_events_outside_claude_code_use_unknown_session(home, repo):
    _log("k", "text")
    (write,) = [e for e in _events(home) if e["command"] == "memory-log"]
    assert write["session"] == "unknown"


def test_telemetry_off_writes_memory_but_no_events(home, repo, in_session):
    (home / "config.md").write_text("---\ntelemetry: 'off'\n---\n")
    assert _log("k", "text").exit_code == 0
    runner.invoke(sdk_app, ["memory-search", "text"])
    runner.invoke(sdk_app, ["context", "--shell", "--skill", "x"])
    assert len(_ledger(home)) == 1
    assert not (home / "events").exists()


def test_context_read_events_carry_ids_never_text_or_files(home, repo, in_session):
    _log("k", "TOPSECRETTEXT", "--files", "src/secret_module.py")
    _log("note", "SCRATCHSECRET", "--scratch")
    result = runner.invoke(sdk_app, ["context", "--shell", "--skill", "dev-ship"])
    assert "TOPSECRETTEXT" in result.stdout
    reads = [e for e in _events(home) if e["command"] == "context" and e["event"] == "context_read"]
    by_file = {e["path"]: e["ids"] for e in reads}
    assert by_file == {"memory.jsonl": ["o-r/k"], "scratch/o-r.jsonl": ["o-r/note"]}
    raw = (home / "events").read_text() if (home / "events").is_file() else "".join(
        f.read_text() for f in (home / "events").glob("*.jsonl"))
    for secret in ("TOPSECRETTEXT", "SCRATCHSECRET", "secret_module"):
        assert secret not in raw


def test_context_shell_block_strips_delimiter_lines(home, repo, monkeypatch):
    import vague.sdk.commands.init as init_module
    from vague.sdk.core.memory import Block

    monkeypatch.setattr(init_module, "render_block",
                        lambda **_: Block(text="a\nVAGUE_MEMORY\nb", ids=[], scratch_ids=[]))
    result = runner.invoke(sdk_app, ["context", "--shell", "--skill", "x"])
    assert result.stdout.count("VAGUE_MEMORY") == 2


def test_context_shell_block_failure_still_prints_variables(home, repo, monkeypatch):
    import vague.sdk.commands.init as init_module

    def boom(**_):
        raise RuntimeError("broken ledger")

    monkeypatch.setattr(init_module, "render_block", boom)
    result = runner.invoke(sdk_app, ["context", "--shell", "--skill", "x"])
    assert result.exit_code == 0
    assert "SLUG=" in result.stdout and "VAGUE_MEMORY" not in result.stdout


SHELLS = [name for name in ("bash", "zsh") if shutil.which(name)]


@pytest.mark.parametrize("shell", SHELLS)
def test_eval_preamble_in_real_shell_sets_vars_and_prints_block(home, repo, shell):
    for i in range(500):
        scope = "global" if i % 5 == 0 else "o-r"
        append_memory(memory=Memory(ts=datetime.now(UTC), scope=scope, key=f"key-{i}", kind="learning",
                                    text=f"fact {i} with $HOME and `backticks` " + "w" * 150))
    env = {**os.environ, "PATH": f"{Path(sys.executable).parent}{os.pathsep}{os.environ['PATH']}"}
    script = 'eval "$(vague context --shell --skill dev-ship)"\nprintf "SLUG_IS=%s\\n" "$SLUG"'
    proc = subprocess.run([shell, "-c", script], cwd=repo, env=env, capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout
    assert out.splitlines()[-1] == "SLUG_IS=o-r"
    block = out.rsplit("\nSLUG_IS=", 1)[0]
    assert block.startswith("vague memory")
    assert "$HOME and `backticks`" in block
    assert len(block) <= BLOCK_LIMIT
    assert "warning" not in proc.stderr.lower()


def test_ledger_path_respects_vague_home(home):
    assert ledger_path() == home / "memory.jsonl"
