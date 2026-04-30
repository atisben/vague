"""Shared test fixtures."""

import os
import pytest
from pathlib import Path


@pytest.fixture
def vague_home(tmp_path):
    """Create a temporary VAGUE_HOME directory and set env var."""
    home = tmp_path / ".vague"
    home.mkdir()
    os.environ["VAGUE_HOME"] = str(home)
    yield home
    del os.environ["VAGUE_HOME"]


@pytest.fixture
def git_repo(tmp_path):
    """Create a minimal git repo for testing."""
    import subprocess
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    subprocess.run(["git", "init"], cwd=str(repo_dir), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(repo_dir), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(repo_dir), capture_output=True)
    # Make an initial commit
    (repo_dir / "README.md").write_text("# Test")
    subprocess.run(["git", "add", "."], cwd=str(repo_dir), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(repo_dir), capture_output=True)
    return repo_dir
