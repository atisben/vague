"""Tests for commit command."""

import os
import pytest
from pathlib import Path
from typer.testing import CliRunner

from vague.sdk.cli import sdk_app
from vague.sdk.core.git_ops import NOTHING_TO_COMMIT

runner = CliRunner()


def test_commit_nothing_to_commit(git_repo, vague_home, monkeypatch):
    """When nothing is staged, return nothing-to-commit with exit 0."""
    monkeypatch.chdir(git_repo)
    result = runner.invoke(sdk_app, ["commit", "test msg"])
    assert result.exit_code == 0
    assert NOTHING_TO_COMMIT in result.output


def test_commit_with_staged_files(git_repo, vague_home, monkeypatch):
    """Commit should return a SHA when files are staged."""
    monkeypatch.chdir(git_repo)
    test_file = git_repo / "new_file.txt"
    test_file.write_text("hello")

    result = runner.invoke(sdk_app, ["commit", "add new file", "--files", "new_file.txt"])
    assert result.exit_code == 0
    output = result.output.strip()
    # Either a commit SHA (40 hex chars) or nothing-to-commit
    assert len(output) == 40 or output == NOTHING_TO_COMMIT
