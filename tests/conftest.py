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


@pytest.fixture(autouse=True)
def clear_claude_session_id(monkeypatch):
    """Run every test as if outside Claude Code.

    The real suite runs inside a Claude Code session where this variable is set,
    which would make every vague command log context events. Tests that need
    the variable set it explicitly.
    """
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)


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
def make_memory():
    """Factory for Memory records with defaults, so a test names only the fields it cares about."""
    from datetime import UTC, datetime

    from vague.sdk.core.memory import Memory

    def _make(**fields):
        defaults = {
            "ts": datetime(2026, 11, 1, tzinfo=UTC), "scope": "o-r", "key": "k", "kind": "learning",
            "text": "some fact",
        }
        return Memory(**{**defaults, **fields})

    return _make


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


@pytest.fixture
def hook_payload():
    """Factory for a Claude Code PostToolUse payload, so a test names only the tool and its input."""

    def _make(tool_name="Write", tool_input=None, session_id="s1", cwd="/nonexistent/dir/for/tests", **extra):
        payload = {
            "hook_event_name": "PostToolUse", "tool_name": tool_name, "tool_input": tool_input or {},
            "session_id": session_id, "cwd": cwd,
        }
        return {**payload, **extra}

    return _make


@pytest.fixture
def skill_dir(tmp_path):
    """Factory that writes a SKILL.md into tmp_path and returns its directory.

    The defaults pass every skill rule, so a test names only the field or line it breaks.
    """
    import frontmatter as frontmatter_lib

    def _make(name="demo-skill", fields=None, omit=(), body=None, root=None):
        defaults = {
            "name": name,
            "version": "1.0.0",
            "description": "A test skill",
            "sdk_commands": ["vague context"],
            "allowed-tools": ["Bash"],
        }
        frontmatter = {k: v for k, v in {**defaults, **(fields or {})}.items() if k not in omit}
        if body is None:
            body = f'## Preamble\n\n```bash\neval "$(vague context --shell --skill {name})"\n```\n'
        directory = (root or tmp_path) / name
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "SKILL.md").write_text(
            frontmatter_lib.dumps(frontmatter_lib.Post(body, **frontmatter)), encoding="utf-8"
        )
        return directory

    return _make
