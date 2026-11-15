"""Tests for vague/memory.py."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from vague.cli import app
from vague.log import get_logger
from vague.memory import (
    BLOCK_LIMIT,
    FULL_LIMIT,
    SCRATCH_LIMIT,
    Memory,
    append_memory,
    changed_files,
    fold,
    ledger_path,
    load_ledger,
    rank,
    read_lines,
    render_block,
    search,
)

NOW = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)


def _append_many(args):
    home, worker, count = args
    os.environ["VAGUE_HOME"] = home
    for i in range(count):
        append_memory(memory=Memory(
            ts=datetime.now(UTC), scope="o-r", key=f"w{worker}-{i}", kind="learning", text="x" * 300,
        ))


def test_append_memory_writes_one_parseable_line_without_none_fields(make_memory):
    append_memory(memory=make_memory(key="a", text="hello"))
    lines = ledger_path().read_text().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["key"] == "a" and row["text"] == "hello"
    assert "skill" not in row


def test_append_memory_two_processes_lose_no_lines():
    home = os.environ["VAGUE_HOME"]
    with ProcessPoolExecutor(max_workers=2) as ex:
        list(ex.map(_append_many, [(home, 0, 100), (home, 1, 100)]))
    lines = ledger_path().read_text().splitlines()
    assert len(lines) == 200
    assert all(json.loads(line)["key"] for line in lines)


def test_fold_same_scope_and_key_returns_latest_text(make_memory):
    lines = [
        make_memory(key="a", text="old", files=["x.py"], skill="dev-ship"),
        make_memory(key="b", text="other"),
        make_memory(key="a", text="new", ts=NOW),
    ]
    folded = {m.key: m for m in fold(lines=lines)}
    assert folded["a"].text == "new"
    assert folded["a"].files == ["x.py"] and folded["a"].skill == "dev-ship"
    assert folded["a"].ts == NOW
    assert folded["b"].text == "other"


def test_fold_same_key_in_two_scopes_keeps_both(make_memory):
    folded = fold(lines=[make_memory(scope="a", key="k"), make_memory(scope="b", key="k")])
    assert len(folded) == 2


def test_fold_status_only_line_forgets_and_keeps_history(make_memory):
    append_memory(memory=make_memory(key="a", text="remember me"))
    append_memory(memory=make_memory(key="a", text=None, status="forgotten"))
    (folded,) = load_ledger()
    assert folded.status == "forgotten" and folded.text == "remember me"
    assert "remember me" in ledger_path().read_text()
    assert search(words=["remember"], scopes=["o-r"]) == []
    assert "remember me" not in render_block(scope="o-r", skill=None, changed_files=[]).text


def test_read_lines_skips_torn_last_line_with_warning(make_memory, monkeypatch):
    append_memory(memory=make_memory(key="a"))
    append_memory(memory=make_memory(key="b"))
    with ledger_path().open("a") as f:
        f.write('{"ts":"2026-11-11T00:00:00Z","scope":"o-r","ke')
    warnings = []
    monkeypatch.setattr(get_logger(), "warning", lambda *args: warnings.append(args))
    assert [m.key for m in read_lines(path=ledger_path())] == ["a", "b"]
    assert len(warnings) == 1


def test_read_lines_missing_file_returns_empty(tmp_path):
    assert read_lines(path=tmp_path / "nope.jsonl") == []


def test_rank_memory_with_changed_file_overlap_comes_first(make_memory):
    memories = [
        make_memory(key="newest", ts=NOW),
        make_memory(key="skill", skill="dev-ship"),
        make_memory(key="files", files=["src/a.py"], ts=NOW - timedelta(days=90)),
    ]
    ranked = rank(memories=memories, skill="dev-ship", changed_files=["src/a.py"])
    assert [m.key for m in ranked] == ["files", "skill", "newest"]


def test_rank_without_overlap_or_skill_orders_newest_first(make_memory):
    memories = [make_memory(key="old", ts=NOW - timedelta(days=2)), make_memory(key="new", ts=NOW)]
    assert [m.key for m in rank(memories=memories, skill=None, changed_files=[])] == ["new", "old"]


def test_render_block_empty_ledger_says_no_memories_yet():
    block = render_block(scope="o-r", skill=None, changed_files=[])
    assert "No memories yet" in block.text
    assert block.ids == [] and block.scratch_ids == []


def test_render_block_shows_scope_and_global_learnings_but_never_observations(make_memory):
    append_memory(memory=make_memory(key="local", text="LOCALFACT"))
    append_memory(memory=make_memory(scope="global", key="glob", text="GLOBALFACT"))
    append_memory(memory=make_memory(scope="other", key="elsewhere", text="OTHERFACT"))
    append_memory(memory=make_memory(scope="global", key="obs", kind="observation", text="OBSFACT"))
    block = render_block(scope="o-r", skill=None, changed_files=[])
    assert "- [local] LOCALFACT" in block.text
    assert "- [global/glob] GLOBALFACT" in block.text
    assert "OTHERFACT" not in block.text and "OBSFACT" not in block.text
    assert sorted(block.ids) == ["global/glob", "o-r/local"]


def test_render_block_500_memories_stays_within_budget(make_memory):
    for i in range(500):
        scope = "global" if i % 4 == 0 else "o-r"
        append_memory(memory=make_memory(scope=scope, key=f"key-{i}", text=f"fact {i} " + "w" * 200))
    block = render_block(scope="o-r", skill=None, changed_files=[])
    assert len(block.text) <= BLOCK_LIMIT
    assert "more: vague memory-search <words>" in block.text.splitlines()[-1]


def test_render_block_global_full_lines_capped_at_one_third(make_memory):
    for i in range(60):
        append_memory(memory=make_memory(scope="global", key=f"g-{i}", text="g" * 150, ts=NOW))
        append_memory(memory=make_memory(key=f"l-{i}", text="l" * 150, ts=NOW - timedelta(days=1)))
    block = render_block(scope="o-r", skill=None, changed_files=[])
    full = [line for line in block.text.splitlines() if line.startswith("- [") and "] " in line]
    global_chars = sum(len(line) + 1 for line in full if line.startswith("- [global/"))
    assert global_chars > 0
    assert global_chars <= FULL_LIMIT / 3
    assert sum(len(line) + 1 for line in full) <= FULL_LIMIT


def test_render_block_overlapping_memory_is_first_full_line(make_memory):
    for i in range(5):
        append_memory(memory=make_memory(key=f"k{i}", ts=NOW))
    append_memory(memory=make_memory(key="touches-a", files=["src/a.py"], ts=NOW - timedelta(days=300)))
    block = render_block(scope="o-r", skill=None, changed_files=["src/a.py"])
    first = next(line for line in block.text.splitlines() if line.startswith("- ["))
    assert first.startswith("- [touches-a]")


def test_render_block_scratch_section_capped_and_expired_hidden(make_memory):
    append_memory(memory=make_memory(key="stale-note", kind="note", text="OLDNOTE", ts=NOW - timedelta(days=8)))
    for i in range(30):
        append_memory(memory=make_memory(key=f"note-{i}", kind="note", text="n" * 100, ts=NOW))
    block = render_block(scope="o-r", skill=None, changed_files=[], now=NOW)
    assert "OLDNOTE" not in block.text
    lines = block.text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("Scratch"))
    section = []
    for line in lines[start:]:
        if line.startswith("Memories") or line.startswith("No memories"):
            break
        section.append(line)
    assert 0 < len("\n".join(section)) <= SCRATCH_LIMIT
    assert block.scratch_ids and "o-r/stale-note" not in block.scratch_ids


def test_search_ands_words_across_key_text_and_files(make_memory):
    append_memory(memory=make_memory(key="docker-tests", text="run task tests", files=["Taskfile.yml"]))
    append_memory(memory=make_memory(key="docker-other", text="unrelated"))
    hits = search(words=["DOCKER", "taskfile", "run"], scopes=["o-r"])
    assert [m.key for m in hits] == ["docker-tests"]


def test_search_scopes_and_kind_filter(make_memory):
    append_memory(memory=make_memory(scope="a", key="x", text="needle"))
    append_memory(memory=make_memory(scope="b", key="y", text="needle"))
    append_memory(memory=make_memory(scope="global", key="z", kind="observation", text="needle"))
    assert [m.scope for m in search(words=["needle"], scopes=["a"])] == ["a"]
    assert len(search(words=["needle"], scopes=None)) == 3
    assert [m.key for m in search(words=["needle"], scopes=None, kind="observation")] == ["z"]


def test_note_is_hidden_after_seven_days(make_memory):
    append_memory(memory=make_memory(key="old", kind="note", text="needle", ts=NOW - timedelta(days=8)))
    append_memory(memory=make_memory(key="fresh", kind="note", text="needle", ts=NOW - timedelta(days=6)))
    append_memory(memory=make_memory(key="old-fact", text="needle", ts=NOW - timedelta(days=30)))
    assert [m.key for m in search(words=["needle"], scopes=["o-r"], kind="note", now=NOW)] == ["fresh"]
    assert [m.key for m in search(words=["needle"], scopes=["o-r"], now=NOW)] == ["fresh", "old-fact"]
    block = render_block(scope="o-r", skill=None, changed_files=[], now=NOW)
    assert block.scratch_ids == ["o-r/fresh"]


def test_search_scratch_returns_only_notes(make_memory):
    append_memory(memory=make_memory(key="note", kind="note", text="needle", ts=NOW))
    append_memory(memory=make_memory(key="fact", text="needle", ts=NOW))
    append_memory(memory=make_memory(key="plan", kind="doc", text="needle", files=["/p.md"], ts=NOW))
    assert [m.key for m in search(words=["needle"], scopes=["o-r"], kind="note", now=NOW)] == ["note"]


def test_doc_is_excluded_from_the_ranked_block(make_memory):
    append_memory(memory=make_memory(key="fact", text="LEARNINGTEXT"))
    append_memory(memory=make_memory(key="eng-plan-main", kind="doc", text="DOCTEXT", files=["/plans/p.md"]))
    block = render_block(scope="o-r", skill=None, changed_files=[])
    ranked = block.text.split("Memories (most relevant first):", 1)[1]
    assert "- [fact] LEARNINGTEXT" in ranked
    assert "eng-plan-main" not in ranked and "DOCTEXT" not in block.text


def test_block_lists_newest_docs_as_key_and_path(make_memory):
    for i in range(7):
        append_memory(memory=make_memory(key=f"doc-{i}", kind="doc", text="Saved.", files=[f"/d/{i}.md"],
                                         ts=NOW - timedelta(days=7 - i)))
    append_memory(memory=make_memory(scope="other", key="theirs", kind="doc", files=["/x.md"], ts=NOW))
    block = render_block(scope="o-r", skill=None, changed_files=[], now=NOW)
    lines = block.text.splitlines()
    start = lines.index("Documents (newest 5, vague memory-search --kind doc for more):")
    assert lines[start + 1:start + 6] == [f"- [doc-{i}] /d/{i}.md" for i in (6, 5, 4, 3, 2)]
    assert "theirs" not in block.text
    assert "o-r/doc-6" in block.ids and "o-r/doc-1" not in block.ids


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=cwd, check=True,
                   capture_output=True)


def test_changed_files_lists_modified_and_untracked(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    (repo / "tracked.py").write_text("a")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "init")
    (repo / "tracked.py").write_text("b")
    (repo / "sub").mkdir()
    (repo / "sub" / "new.py").write_text("c")
    assert sorted(changed_files(cwd=repo / "sub")) == ["sub/new.py", "tracked.py"]


def test_changed_files_outside_repo_is_empty(tmp_path):
    assert changed_files(cwd=tmp_path) == []


runner = CliRunner()


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


def _ledger(vague_home: Path) -> list[dict]:
    path = vague_home / "memory.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def _events(vague_home: Path) -> list[dict]:
    events_dir = vague_home / "events"
    files = sorted(events_dir.glob("*.jsonl")) if events_dir.is_dir() else []
    return [json.loads(line) for f in files for line in f.read_text().splitlines()]


def _log(*args: str):
    return runner.invoke(app, ["memory-log", *args])


def test_memory_log_appends_one_parseable_line(vague_home, repo):
    result = _log("tests-need-docker", "Run task tests.", "--files", "Taskfile.yml, src/a.py")
    assert result.exit_code == 0, result.output
    assert result.stdout.strip() == "OK o-r/tests-need-docker"
    (row,) = _ledger(vague_home)
    assert (row["scope"], row["key"], row["kind"], row["text"]) == ("o-r", "tests-need-docker", "learning",
                                                                    "Run task tests.")
    assert row["files"] == ["Taskfile.yml", "src/a.py"]
    assert row["status"] == "active"


def test_memory_log_global_writes_global_scope(vague_home, repo):
    assert _log("verify-subagents", "Check the seams yourself.", "--global").exit_code == 0
    assert _ledger(vague_home)[0]["scope"] == "global"


def test_memory_log_in_home_without_global_exits_1_and_writes_nothing(vague_home, tmp_path, monkeypatch):
    fake_home = tmp_path / "me"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.chdir(fake_home)
    result = _log("k", "text")
    assert result.exit_code == 1
    assert "--global" in result.stderr
    assert not (vague_home / "memory.jsonl").exists()
    assert _log("k", "text", "--global").exit_code == 0


def test_memory_log_about_writes_global_observation(vague_home, repo):
    assert _log("ship-skips-tests", "dev-ship skipped the suite.", "--about", "dev-ship").exit_code == 0
    (row,) = _ledger(vague_home)
    assert (row["scope"], row["kind"], row["skill"]) == ("global", "observation", "dev-ship")


def test_memory_log_without_text_or_status_errors(vague_home, repo):
    result = _log("k")
    assert result.exit_code == 1
    assert not (vague_home / "memory.jsonl").exists()


def test_memory_log_text_over_600_chars_errors(vague_home, repo):
    result = _log("k", "x" * 601)
    assert result.exit_code == 1
    assert "600" in result.stderr
    assert not (vague_home / "memory.jsonl").exists()


def test_memory_log_bad_status_errors(vague_home, repo):
    assert _log("k", "--status", "deleted").exit_code == 1


def test_memory_log_status_only_forgets_and_keeps_history(vague_home, repo):
    _log("k", "SECRETFACT")
    result = _log("k", "--status", "forgotten")
    assert result.exit_code == 0
    rows = _ledger(vague_home)
    assert len(rows) == 2 and "text" not in rows[1] and rows[1]["status"] == "forgotten"
    assert "SECRETFACT" not in runner.invoke(app, ["memory-search", "secretfact"]).stdout
    assert "SECRETFACT" not in runner.invoke(app, ["context", "--shell", "--skill", "x"]).stdout


def test_memory_log_status_only_keeps_observation_kind(vague_home, repo):
    _log("obs", "an observation", "--about", "meta")
    assert _log("obs", "--status", "actioned", "--global").exit_code == 0
    assert _ledger(vague_home)[1]["kind"] == "observation"


def test_memory_log_status_only_observation_falls_back_to_global_scope(vague_home, repo):
    _log("obs", "an observation", "--about", "meta")
    result = _log("obs", "--status", "actioned")
    assert result.exit_code == 0, result.output
    assert result.stdout.strip() == "OK global/obs"
    row = _ledger(vague_home)[1]
    assert (row["scope"], row["kind"], row["status"]) == ("global", "observation", "actioned")


def test_memory_log_status_only_prefers_current_scope_over_global(vague_home, repo):
    _log("k", "project fact")
    _log("k", "global fact", "--global")
    assert _log("k", "--status", "forgotten").stdout.strip() == "OK o-r/k"


def test_memory_log_status_only_for_unknown_key_errors(vague_home, repo):
    assert _log("never-logged", "--status", "forgotten").exit_code == 1
    assert not (vague_home / "memory.jsonl").exists()


def test_scratch_flag_writes_a_note(vague_home, repo):
    result = _log("claim-auth-refactor", "agent 2 owns src/auth", "--scratch")
    assert result.exit_code == 0, result.output
    (row,) = _ledger(vague_home)
    assert (row["key"], row["kind"], row["scope"]) == ("claim-auth-refactor", "note", "o-r")
    assert not (vague_home / "scratch").exists()


def test_doc_flag_requires_files(vague_home, repo):
    result = _log("eng-plan-main", "Eng plan for main.", "--doc")
    assert result.exit_code == 1
    assert "--doc" in result.stderr and "--files" in result.stderr
    assert not (vague_home / "memory.jsonl").exists()


def test_doc_flag_writes_a_doc_with_its_deliverable(vague_home, repo, tmp_path):
    plan = tmp_path / "plan.md"
    plan.write_text("# plan")
    result = _log("eng-plan-main", "Eng plan for main.", "--doc", "--files", str(plan), "--skill", "plan-eng")
    assert result.exit_code == 0, result.output
    (row,) = _ledger(vague_home)
    assert (row["kind"], row["skill"], row["files"]) == ("doc", "plan-eng", [str(plan)])


@pytest.mark.parametrize(("first", "second"), [
    (["--scratch"], []),
    ([], ["--scratch"]),
    (["--doc", "--files", "/p.md"], ["--scratch"]),
])
def test_log_rejects_kind_change_on_existing_key(vague_home, repo, first, second):
    assert _log("k", "first", *first).exit_code == 0
    result = _log("k", "second", *second)
    assert result.exit_code == 1
    assert "note" in result.stderr
    assert len(_ledger(vague_home)) == 1


def test_log_allows_learning_to_become_doc(vague_home, repo):
    _log("vault-my-note", "Saved My Note.", "--files", "/vault/My Note.md")
    result = _log("vault-my-note", "My Note in the vault.", "--doc", "--files", "/vault/My Note.md")
    assert result.exit_code == 0, result.output
    assert [row["kind"] for row in _ledger(vague_home)] == ["learning", "doc"]


def test_doc_flag_rejects_about_and_scratch(vague_home, repo):
    assert _log("k", "t", "--doc", "--files", "/p.md", "--scratch").exit_code == 1
    assert _log("k", "t", "--doc", "--files", "/p.md", "--about", "meta").exit_code == 1


def test_memory_search_skill_filter_and_doc_kind(vague_home, repo):
    _log("eng-plan-main", "Eng plan.", "--doc", "--files", "/p.md", "--skill", "plan-eng")
    _log("plan-fact", "A fact about plan-eng.", "--skill", "plan-eng-lite")
    assert _search("--skill", "plan-eng") == ["o-r/eng-plan-main  [plan-eng]  Eng plan.  (files: /p.md)"]
    assert _search("--kind", "doc") == ["o-r/eng-plan-main  [plan-eng]  Eng plan.  (files: /p.md)"]


def test_memory_search_rejects_unknown_kind_and_conflicting_scratch(vague_home, repo):
    assert runner.invoke(app, ["memory-search", "--kind", "nope"]).exit_code == 1
    assert runner.invoke(app, ["memory-search", "--kind", "doc", "--scratch"]).exit_code == 1


def test_memory_search_ands_words_and_logs_served_ids(vague_home, repo, in_session):
    _log("tests-need-docker", "Run task tests in docker.", "--files", "Taskfile.yml")
    _log("docker-other", "Unrelated docker fact.")
    _log("elsewhere", "docker but not the other word", "--global")
    result = runner.invoke(app, ["memory-search", "docker", "taskfile"])
    assert result.exit_code == 0
    assert result.stdout.splitlines() == ["o-r/tests-need-docker  Run task tests in docker.  (files: Taskfile.yml)"]
    (read,) = [e for e in _events(vague_home) if e["command"] == "memory-search"]
    assert read["event"] == "context_read"
    assert read["ids"] == ["o-r/tests-need-docker"]


def test_memory_search_kind_observation_searches_global(vague_home, repo):
    _log("obs", "skill feedback here", "--about", "meta")
    _log("learn", "skill feedback here")
    result = runner.invoke(app, ["memory-search", "feedback", "--kind", "observation"])
    assert result.stdout.splitlines() == ["global/obs  [meta]  skill feedback here"]


def test_memory_search_prints_skill_and_matches_it(vague_home, repo):
    _log("obs-a", "slow step", "--about", "dev-ship")
    _log("obs-b", "slow step", "--about", "retro")
    result = runner.invoke(app, ["memory-search", "dev-ship", "--kind", "observation"])
    assert result.stdout.splitlines() == ["global/obs-a  [dev-ship]  slow step"]


def test_memory_search_prints_files_when_set(vague_home, repo):
    _log("tests-need-docker", "tests run in the container", "--files", "Taskfile.yml,compose.yml")
    _log("no-files", "plain fact")
    result = runner.invoke(app, ["memory-search"])
    lines = sorted(line.split("/", 1)[1] for line in result.stdout.splitlines())
    assert lines == ["no-files  plain fact",
                     "tests-need-docker  tests run in the container  (files: Taskfile.yml, compose.yml)"]


def _put(scope: str, key: str, text: str = "needle", minutes_ago: int = 0, kind: str = "learning") -> None:
    ts = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    append_memory(memory=Memory(ts=ts, scope=scope, key=key, kind=kind, text=text))


def _search(*args: str) -> list[str]:
    return runner.invoke(app, ["memory-search", *args]).stdout.splitlines()


def test_memory_search_default_covers_current_scope_and_global_only(vague_home, repo):
    _put(scope="o-r", key="here")
    _put(scope="global", key="g")
    _put(scope="elsewhere", key="k")
    assert sorted(_search("needle")) == ["global/g  needle", "o-r/here  needle"]


def test_memory_search_scope_global_returns_only_global(vague_home, repo):
    _put(scope="o-r", key="here")
    _put(scope="global", key="g")
    assert _search("needle", "--scope", "global") == ["global/g  needle"]


def test_memory_search_scope_project_returns_only_that_project(vague_home, repo):
    _put(scope="o-r", key="here")
    _put(scope="global", key="g")
    _put(scope="elsewhere", key="k")
    assert _search("needle", "--scope", "elsewhere") == ["elsewhere/k  needle"]


def test_memory_search_scope_all_spans_every_scope(vague_home, repo):
    _put(scope="o-r", key="here", minutes_ago=2)
    _put(scope="global", key="g", minutes_ago=1)
    _put(scope="elsewhere", key="k")
    assert _search("needle", "--scope", "all") == ["elsewhere/k  needle", "global/g  needle", "o-r/here  needle"]


def test_memory_search_scope_unknown_says_no_match(vague_home, repo):
    _put(scope="o-r", key="here")
    result = runner.invoke(app, ["memory-search", "--scope", "nope"])
    assert result.exit_code == 0
    assert result.stdout.strip() == "No memories match."


def test_memory_search_without_words_lists_every_active_memory_newest_first(vague_home, repo, in_session):
    _put(scope="elsewhere", key="old", text="first", minutes_ago=3)
    _put(scope="global", key="mid", text="second", minutes_ago=2)
    _put(scope="other", key="new", text="third", minutes_ago=1)
    _log("gone", "forgotten fact")
    _log("gone", "--status", "forgotten")
    assert _search("--scope", "all") == ["other/new  third", "global/mid  second", "elsewhere/old  first"]
    (read,) = [e for e in _events(vague_home) if e["command"] == "memory-search"]
    assert read["ids"] == ["other/new", "global/mid", "elsewhere/old"]


def test_memory_search_scope_all_scratch_spans_every_scope(vague_home, repo):
    _put(scope="o-r", key="mine", kind="note", minutes_ago=1)
    _put(scope="elsewhere", key="theirs", kind="note")
    _put(scope="o-r", key="fact")
    assert _search("--scratch") == ["o-r/mine  needle"]
    assert _search("--scratch", "--scope", "all") == ["elsewhere/theirs  needle", "o-r/mine  needle"]
    assert _search("--scratch", "--scope", "elsewhere") == ["elsewhere/theirs  needle"]


def test_memory_log_logs_context_write_with_id(vague_home, repo, in_session):
    _log("k", "text")
    (write,) = [e for e in _events(vague_home) if e["command"] == "memory-log"]
    assert write["event"] == "context_write"
    assert write["ids"] == ["o-r/k"]
    assert write["path"] == "memory.jsonl"


def test_events_outside_claude_code_use_unknown_session(vague_home, repo):
    _log("k", "text")
    (write,) = [e for e in _events(vague_home) if e["command"] == "memory-log"]
    assert write["session"] == "unknown"


def test_telemetry_off_writes_memory_but_no_events(vague_home, repo, in_session):
    (vague_home / "config.env").write_text("telemetry=off\n")
    assert _log("k", "text").exit_code == 0
    runner.invoke(app, ["memory-search", "text"])
    runner.invoke(app, ["context", "--shell", "--skill", "x"])
    assert len(_ledger(vague_home)) == 1
    assert not (vague_home / "events").exists()


def test_context_read_events_carry_ids_never_text_or_files(vague_home, repo, in_session):
    _log("k", "TOPSECRETTEXT", "--files", "src/secret_module.py")
    _log("note", "SCRATCHSECRET", "--scratch")
    result = runner.invoke(app, ["context", "--shell", "--skill", "dev-ship"])
    assert "TOPSECRETTEXT" in result.stdout
    reads = [e for e in _events(vague_home) if e["command"] == "context" and e["event"] == "context_read"]
    by_file = {e["path"]: e["ids"] for e in reads}
    assert by_file == {"memory.jsonl": ["o-r/note", "o-r/k"]}
    raw = (vague_home / "events").read_text() if (vague_home / "events").is_file() else "".join(
        f.read_text() for f in (vague_home / "events").glob("*.jsonl"))
    for secret in ("TOPSECRETTEXT", "SCRATCHSECRET", "secret_module"):
        assert secret not in raw


SHELLS = [name for name in ("bash", "zsh") if shutil.which(name)]


@pytest.mark.parametrize("shell", SHELLS)
def test_eval_preamble_in_real_shell_sets_vars_and_prints_block(vague_home, repo, shell):
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


def test_ledger_path_respects_vague_home(vague_home):
    assert ledger_path() == vague_home / "memory.jsonl"


def _files(vague_home: Path) -> list[str]:
    return _ledger(vague_home)[-1]["files"]


def test_memory_log_keeps_an_absolute_path_outside_the_repo(vague_home, repo, tmp_path):
    note = tmp_path / "vault" / "Note.md"
    note.parent.mkdir()
    note.write_text("x")

    assert _log("vault-note", "Saved Note.", "--files", str(note)).exit_code == 0

    assert _files(vague_home) == [str(note)]


def test_memory_log_expands_a_home_relative_path(vague_home, repo, monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / "Obsidian").mkdir()
    (tmp_path / "Obsidian" / "Note.md").write_text("x")

    _log("vault-note", "Saved Note.", "--files", "~/Obsidian/Note.md")

    assert _files(vague_home) == [str(tmp_path / "Obsidian" / "Note.md")]


def test_memory_log_makes_an_absolute_path_inside_the_repo_relative(vague_home, repo):
    _log("tests-need-docker", "Run it.", "--files", str(repo / "Taskfile.yml"))

    assert _files(vague_home) == ["Taskfile.yml"]


def test_memory_log_keeps_a_filename_with_a_comma_whole_when_it_exists(vague_home, repo, tmp_path):
    note = tmp_path / "Perf Review, H1.md"
    note.write_text("x")

    _log("vault-note", "Saved.", "--files", str(note))

    assert _files(vague_home) == [str(note)]


def test_memory_log_accepts_the_files_option_more_than_once(vague_home, repo):
    _log("two-files", "Both matter.", "--files", "a.py", "--files", "b.py")

    assert _files(vague_home) == ["a.py", "b.py"]


def test_memory_log_drops_duplicate_files(vague_home, repo):
    _log("dupes", "Once.", "--files", "a.py,a.py", "--files", "a.py")

    assert _files(vague_home) == ["a.py"]
