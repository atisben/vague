"""Tests for vague.sdk.core.slug.get_git_context and the git fields on events."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from vague.sdk.core import slug as slug_module
from vague.sdk.core.events import parse_hook_payload
from vague.sdk.core.slug import get_git_context

NOW = datetime(2026, 11, 11, 10, 0, 0, tzinfo=UTC)


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=cwd, check=True, capture_output=True,
    )


def _make_repo(parent: Path, name: str = "repo", commit: bool = True) -> Path:
    repo = parent / name
    repo.mkdir(parents=True)
    _git(repo, "init", "-b", "main")
    if commit:
        _git(repo, "commit", "--allow-empty", "-m", "init")
    return repo


def _event(cwd: Path):
    event = parse_hook_payload(
        payload={
            "hook_event_name": "PostToolUse", "tool_name": "Skill", "tool_input": {"skill": "learn"},
            "tool_response": {"success": True}, "session_id": "s", "cwd": str(cwd),
        },
        now=NOW,
    )
    assert event is not None
    return event


def test_context_normal_repo_has_root_equal_main_root(tmp_path):
    repo = _make_repo(tmp_path)
    ctx = get_git_context(cwd=repo)
    assert ctx.in_repo is True
    assert ctx.root == repo.resolve()
    assert ctx.main_root == ctx.root
    assert ctx.is_worktree is False
    assert ctx.branch == "main"


def test_context_linked_worktree_points_main_root_at_main_repo(tmp_path):
    repo = _make_repo(tmp_path)
    wt = tmp_path / "wt"
    _git(repo, "worktree", "add", "-b", "feature", str(wt))
    ctx = get_git_context(cwd=wt)
    assert ctx.root == wt.resolve()
    assert ctx.main_root == repo.resolve()
    assert ctx.is_worktree is True
    assert ctx.branch == "feature"


def test_context_subdirectory_resolves_root_to_toplevel(tmp_path):
    repo = _make_repo(tmp_path)
    sub = repo / "a" / "b"
    sub.mkdir(parents=True)
    ctx = get_git_context(cwd=sub)
    assert ctx.root == repo.resolve()
    assert ctx.main_root == repo.resolve()


def test_context_non_git_directory_falls_back_to_cwd(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    ctx = get_git_context(cwd=plain)
    assert ctx.in_repo is False
    assert ctx.root == plain
    assert ctx.main_root == plain
    assert ctx.is_worktree is False
    assert ctx.branch == "unknown"


def test_context_detached_head_gives_unknown_branch(tmp_path):
    repo = _make_repo(tmp_path)
    _git(repo, "checkout", "--detach")
    ctx = get_git_context(cwd=repo)
    assert ctx.branch == "unknown"
    assert ctx.root == repo.resolve()


def test_context_repo_without_commits_does_not_crash(tmp_path):
    repo = _make_repo(tmp_path, commit=False)
    ctx = get_git_context(cwd=repo)
    assert ctx.in_repo is True
    assert ctx.root == repo.resolve()
    assert ctx.main_root == repo.resolve()
    assert ctx.is_worktree is False


def test_context_bare_repo_falls_back_to_cwd(tmp_path):
    bare = tmp_path / "bare.git"
    bare.mkdir()
    _git(bare, "init", "--bare")
    ctx = get_git_context(cwd=bare)
    assert ctx.root == bare
    assert ctx.main_root == bare
    assert ctx.is_worktree is False


def test_context_worktree_of_bare_repo_uses_worktree_as_main_root(tmp_path):
    bare = tmp_path / "bare.git"
    bare.mkdir()
    _git(bare, "init", "--bare", "-b", "main")
    seed = _make_repo(tmp_path, name="seed")
    _git(seed, "push", str(bare), "main")
    wt = tmp_path / "wt"
    _git(bare, "worktree", "add", str(wt), "main")
    ctx = get_git_context(cwd=wt)
    assert ctx.is_worktree is True
    assert ctx.root == wt.resolve()
    # The common dir is bare.git, not <main>/.git, so there is no main checkout to name.
    assert ctx.main_root == ctx.root


def test_context_submodule_is_its_own_main_root(tmp_path):
    sub_origin = _make_repo(tmp_path, name="sub_origin")
    parent = _make_repo(tmp_path, name="parent")
    subprocess.run(
        ["git", "-c", "protocol.file.allow=always", "-c", "user.email=t@t", "-c", "user.name=t",
         "submodule", "add", str(sub_origin), "sub"],
        cwd=parent, check=True, capture_output=True,
    )
    ctx = get_git_context(cwd=parent / "sub")
    assert ctx.root == (parent / "sub").resolve()
    assert ctx.main_root == ctx.root
    assert ctx.is_worktree is False


def test_context_git_missing_falls_back_without_raising(tmp_path, monkeypatch):
    def boom(*args, **kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(slug_module.subprocess, "run", boom)
    ctx = get_git_context(cwd=tmp_path)
    assert ctx.in_repo is False
    assert ctx.root == tmp_path
    assert ctx.main_root == tmp_path
    assert ctx.branch == "unknown"


def test_context_git_timeout_falls_back_without_raising(tmp_path, monkeypatch):
    def slow(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="git", timeout=5)

    monkeypatch.setattr(slug_module.subprocess, "run", slow)
    assert get_git_context(cwd=tmp_path).root == tmp_path


def test_event_in_worktree_links_to_main_repo_with_same_slug(tmp_path):
    repo = _make_repo(tmp_path)
    _git(repo, "remote", "add", "origin", "https://github.com/o/r.git")
    wt = tmp_path / "wt"
    _git(repo, "worktree", "add", "-b", "feature", str(wt))
    main_event, wt_event = _event(repo), _event(wt)
    assert wt_event.repo == main_event.repo == "o-r"
    assert wt_event.is_worktree is True and main_event.is_worktree is False
    assert wt_event.root == str(wt.resolve())
    assert wt_event.main_root == main_event.main_root == str(repo.resolve())


def test_event_in_non_git_directory_uses_cwd_for_roots(tmp_path):
    event = _event(tmp_path)
    assert event.root == event.main_root == str(tmp_path)
    assert event.is_worktree is False


def test_event_remoteless_repos_with_same_folder_name_have_different_main_root(tmp_path):
    first = _make_repo(tmp_path / "one", name="app")
    second = _make_repo(tmp_path / "two", name="app")
    a, b = _event(first), _event(second)
    assert a.repo == b.repo == "app"
    assert a.main_root != b.main_root


def test_event_in_remoteless_repo_subdir_uses_toplevel_name_as_slug(tmp_path):
    repo = _make_repo(tmp_path, name="proj")
    sub = repo / "x"
    sub.mkdir()
    assert _event(sub).repo == "proj"


@pytest.mark.parametrize("in_git, expected_calls", [(True, 2), (False, 1)])
def test_event_spawns_at_most_two_git_processes(tmp_path, monkeypatch, in_git, expected_calls):
    target = _make_repo(tmp_path) if in_git else tmp_path / "plain"
    target.mkdir(exist_ok=True)
    calls = []
    real_run = subprocess.run

    def counting(*args, **kwargs):
        calls.append(args[0])
        return real_run(*args, **kwargs)

    monkeypatch.setattr(slug_module.subprocess, "run", counting)
    _event(target)
    assert len(calls) == expected_calls
