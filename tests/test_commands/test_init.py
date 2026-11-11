"""Tests for vague init command."""

import json
import os
from datetime import UTC

from typer.testing import CliRunner

from vague.sdk.cli import sdk_app

runner = CliRunner()


def test_init_returns_valid_json(vague_home):
    result = runner.invoke(sdk_app, ["init"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "slug" in data
    assert "branch" in data
    assert "proactive" in data
    assert "telemetry" in data
    assert "learnings" in data


def test_init_returns_empty_learnings_on_fresh(vague_home):
    result = runner.invoke(sdk_app, ["init"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["learnings"] == []


def test_init_does_not_fail_without_git():
    """init should never fail, even outside a git repo."""
    original = os.getcwd()
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        os.environ["VAGUE_HOME"] = tmpdir + "/.vague"
        try:
            result = runner.invoke(sdk_app, ["init"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "slug" in data
        finally:
            os.chdir(original)
            if "VAGUE_HOME" in os.environ:
                del os.environ["VAGUE_HOME"]


def test_init_returns_top_3_learnings_when_many(vague_home):
    from datetime import datetime

    from vague.models import LearningEntry
    from vague.sdk.core.learnings import append_learning
    from vague.sdk.core.slug import get_slug

    slug = get_slug()
    for i in range(8):
        entry = LearningEntry(
            skill="test",
            type="pitfall",
            key=f"key-{i}",
            insight=f"insight {i}",
            confidence=i + 1,
            source="observed",
            ts=datetime(2024, 1, i + 1, tzinfo=UTC),
        )
        append_learning(slug, entry)

    result = runner.invoke(sdk_app, ["init"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data["learnings"]) == 3


def test_context_skill_prints_context_and_upserts_project_meta(vague_home, git_repo, monkeypatch):
    monkeypatch.chdir(git_repo)
    result = runner.invoke(sdk_app, ["context", "--shell", "--skill", "dev-develop"])
    assert result.exit_code == 0
    for prefix in ("SLUG=", "BRANCH=", "PROACTIVE=", "TELEMETRY="):
        assert prefix in result.output
    assert (vague_home / "projects" / "repo" / "project.md").exists()
    assert not (vague_home / "analytics").exists()


def test_context_json_skill_prints_json_and_upserts_project_meta(vague_home, git_repo, monkeypatch):
    monkeypatch.chdir(git_repo)
    result = runner.invoke(sdk_app, ["context", "--skill", "dev-develop"])
    assert result.exit_code == 0
    assert json.loads(result.output)["slug"] == "repo"
    assert (vague_home / "projects" / "repo" / "project.md").exists()
    assert not (vague_home / "analytics").exists()
