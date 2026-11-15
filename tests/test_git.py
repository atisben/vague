"""Tests for vague.git.run: the one way vague spawns git."""

import subprocess

from vague import git


def test_run_returns_stripped_stdout(git_repo):
    assert git.run("branch", "--show-current", cwd=git_repo) in {"main", "master"}


def test_run_returns_none_on_failure_unless_check_is_off(tmp_path):
    assert git.run("rev-parse", "--show-toplevel", cwd=tmp_path) is None
    assert git.run("rev-parse", "--show-toplevel", cwd=tmp_path, check=False) == ""


def test_run_returns_none_when_git_is_missing_or_slow(tmp_path, monkeypatch):
    def missing(*args, **kwargs):
        raise FileNotFoundError("git")

    def slow(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="git", timeout=5)

    monkeypatch.setattr(git.subprocess, "run", missing)
    assert git.run("status", cwd=tmp_path) is None
    monkeypatch.setattr(git.subprocess, "run", slow)
    assert git.run("status", cwd=tmp_path) is None
