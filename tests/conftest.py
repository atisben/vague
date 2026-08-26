"""Shared test fixtures."""

import os

import pytest


@pytest.fixture
def vague_home(tmp_path):
    """Create a temporary VAGUE_HOME directory and set env var."""
    home = tmp_path / ".vague"
    home.mkdir()
    os.environ["VAGUE_HOME"] = str(home)
    yield home
    del os.environ["VAGUE_HOME"]


@pytest.fixture(autouse=True)
def isolate_claude_env(tmp_path, monkeypatch):
    """Keep the developer's own Claude profile config out of the test run.

    Clearing the env vars is not enough: claude_dirs() also reads
    $VAGUE_HOME/config.env, so an unset VAGUE_HOME would fall back to the real
    ~/.vague and pick up whatever profiles the developer has configured.
    Pointing VAGUE_HOME at an empty tmp dir closes both routes.
    """
    for var in ("VAGUE_CLAUDE_DIRS", "CLAUDE_CONFIG_DIR"):
        monkeypatch.delenv(var, raising=False)

    isolated_home = tmp_path / "isolated-vague-home"
    isolated_home.mkdir(exist_ok=True)
    monkeypatch.setenv("VAGUE_HOME", str(isolated_home))


@pytest.fixture
def vague_home_dir(tmp_path):
    """Create a temporary VAGUE_HOME directory without touching the environment.

    Tests that need the env var set should do so with monkeypatch, so the
    lookup order under test stays explicit.
    """
    home = tmp_path / ".vague"
    home.mkdir()
    return home


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
