"""Tests for vague init command."""

import json
import os
import pytest
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
    from datetime import datetime, timezone
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
            ts=datetime(2024, 1, i + 1, tzinfo=timezone.utc),
        )
        append_learning(slug, entry)

    result = runner.invoke(sdk_app, ["init"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data["learnings"]) == 3
