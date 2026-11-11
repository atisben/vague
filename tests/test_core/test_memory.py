"""Tests for vague.sdk.core.memory: the global ledger, fold, ranking, preamble block and search."""

from __future__ import annotations

import json
import os
import subprocess
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from vague.sdk.core import memory as memory_module
from vague.sdk.core.logging import get_logger
from vague.sdk.core.memory import (
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
    scratch_path,
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


def test_append_memory_rejects_text_over_600_chars(make_memory):
    with pytest.raises(ValueError):
        append_memory(memory=make_memory(text="x" * 601))
    assert not ledger_path().exists()


def test_append_memory_scratch_goes_to_scope_file_not_ledger(make_memory):
    append_memory(memory=make_memory(scope="o-r", key="note"), scratch=True)
    assert scratch_path(scope="o-r").read_text().count("\n") == 1
    assert not ledger_path().exists()


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
    append_memory(memory=make_memory(key="stale-note", text="OLDNOTE", ts=NOW - timedelta(days=8)), scratch=True)
    for i in range(30):
        append_memory(memory=make_memory(key=f"note-{i}", text="n" * 100, ts=NOW), scratch=True)
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


def test_search_matches_words_in_skill_field(make_memory):
    append_memory(memory=make_memory(key="obs-a", kind="observation", text="slow step", skill="dev-ship"))
    append_memory(memory=make_memory(key="obs-b", kind="observation", text="slow step", skill="retro"))
    hits = search(words=["dev-ship", "slow"], scopes=["o-r"])
    assert [m.key for m in hits] == ["obs-a"]


def test_search_scopes_and_kind_filter(make_memory):
    append_memory(memory=make_memory(scope="a", key="x", text="needle"))
    append_memory(memory=make_memory(scope="b", key="y", text="needle"))
    append_memory(memory=make_memory(scope="global", key="z", kind="observation", text="needle"))
    assert [m.scope for m in search(words=["needle"], scopes=["a"])] == ["a"]
    assert len(search(words=["needle"], scopes=None)) == 3
    assert [m.key for m in search(words=["needle"], scopes=None, kind="observation")] == ["z"]


def test_search_scratch_hides_notes_older_than_seven_days(make_memory):
    append_memory(memory=make_memory(key="old", text="needle", ts=NOW - timedelta(days=8)), scratch=True)
    append_memory(memory=make_memory(key="fresh", text="needle", ts=NOW - timedelta(days=6)), scratch=True)
    hits = search(words=["needle"], scopes=["o-r"], scratch=True, now=NOW)
    assert [m.key for m in hits] == ["fresh"]


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


def test_load_ledger_reads_env_home(make_memory, vague_home_dir, monkeypatch):
    monkeypatch.setenv("VAGUE_HOME", str(vague_home_dir))
    append_memory(memory=make_memory())
    assert (vague_home_dir / "memory.jsonl").exists()
    assert memory_module.vague_home() == vague_home_dir
