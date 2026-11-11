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


LONG_INSIGHT = "x" * 650


@pytest.fixture
def old_stores(vague_home, tmp_path):
    """Pre-ledger per-project stores for two projects, in the frontmatter formats `vague migrate` reads.

    `o-r` has every store plus a design, a diagram and a lock file. `bastien` holds the
    mgmt-review learning that the owner moved to the `Obsidian` scope.
    """
    from vague.sdk.core.frontmatter import write_md

    live_repo = tmp_path / "live-repo"
    live_repo.mkdir()
    projects = vague_home / "projects"
    write_md(projects / "o-r" / "learnings.md", {"entries": [
        {"skill": "ship", "type": "pitfall", "key": "tests-need-docker", "insight": "Run tests in docker.",
         "confidence": 8, "source": "observed", "files": ["Taskfile.yml"], "ts": "2026-09-01T10:00:00Z"},
        {"skill": "review", "type": "pattern", "key": "long-one", "insight": LONG_INSIGHT,
         "confidence": 5, "source": "observed", "files": [], "ts": "2026-09-02T10:00:00Z"},
    ]})
    write_md(projects / "o-r" / "observations.md", {"entries": [
        {"id": 1, "skill": "investigate", "type": "gap", "issue": "Skips repro", "suggestion": "Add a repro step",
         "principle": "evidence first", "status": "open", "source_skill": "ship", "session": "", "ts":
         "2026-09-03T10:00:00Z"},
        {"id": 2, "skill": "ops-vault", "type": "gap", "issue": "Wrong folder", "suggestion": "Route by type",
         "principle": "one home per thing", "status": "actioned", "source_skill": "vault", "session": "s9",
         "ts": "2026-09-04T10:00:00Z"},
    ]})
    write_md(projects / "o-r" / "timeline.md", {"entries": [
        {"skill": "ship", "event": "completed", "branch": "main", "session": "s1", "outcome": "success",
         "ts": "2026-09-05T10:00:00Z"},
        {"skill": "develop", "event": "started", "branch": "feat", "session": "", "outcome": "",
         "ts": "2026-10-06T10:00:00Z"},
    ]})
    write_md(projects / "o-r" / "project.md", {"path": str(live_repo), "last_seen": "2026-10-07T10:00:00Z"})
    (projects / "o-r" / "learnings.md.lock").write_text("")
    (projects / "o-r" / "designs").mkdir()
    (projects / "o-r" / "designs" / "plan.md").write_text("# plan")
    (projects / "o-r" / "diagrams").mkdir()
    (projects / "o-r" / "diagrams" / "map.html").write_text("<svg/>")
    write_md(projects / "bastien" / "learnings.md", {"entries": [
        {"skill": "mgmt-review", "type": "pattern", "key": "review-evidence", "insight": "Quote the log.",
         "confidence": 7, "source": "observed", "files": [], "ts": "2026-08-01T10:00:00Z"},
    ]})
    write_md(projects / "bastien" / "project.md", {"path": "/nonexistent/bastien", "last_seen":
                                                   "2026-08-02T10:00:00Z"})
    return vague_home


@pytest.fixture
def snapshot():
    """Every file under a directory as {relative path: bytes}, to prove a command wrote nothing."""
    def _snap(root):
        return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}

    return _snap
