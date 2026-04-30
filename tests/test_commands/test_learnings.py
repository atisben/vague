"""Tests for learnings commands."""

import json
import pytest
from typer.testing import CliRunner

from vague.sdk.cli import sdk_app

runner = CliRunner()


def _learning_json(**kwargs):
    defaults = {
        "skill": "test",
        "type": "pitfall",
        "key": "test-key",
        "insight": "Test insight",
        "confidence": 7,
        "source": "observed",
        "ts": "2024-01-01T00:00:00+00:00",
    }
    defaults.update(kwargs)
    return json.dumps(defaults)


def test_learnings_log_and_search(vague_home):
    result = runner.invoke(sdk_app, ["learnings-log", _learning_json(key="my-key")])
    assert result.exit_code == 0
    assert "OK" in result.output

    result = runner.invoke(sdk_app, ["learnings-search"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert any(e["key"] == "my-key" for e in data)


def test_learnings_search_type_filter(vague_home):
    runner.invoke(sdk_app, ["learnings-log", _learning_json(key="k1", type="pitfall")])
    runner.invoke(sdk_app, ["learnings-log", _learning_json(key="k2", type="pattern")])

    result = runner.invoke(sdk_app, ["learnings-search", "--type", "pitfall"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0]["type"] == "pitfall"


def test_learnings_duplicate_key_type_returns_latest(vague_home):
    old = _learning_json(key="dup", insight="old", ts="2024-01-01T00:00:00+00:00")
    new = _learning_json(key="dup", insight="new", ts="2024-06-01T00:00:00+00:00")

    runner.invoke(sdk_app, ["learnings-log", old])
    runner.invoke(sdk_app, ["learnings-log", new])

    result = runner.invoke(sdk_app, ["learnings-search"])
    data = json.loads(result.output)
    dup_entries = [e for e in data if e["key"] == "dup"]
    assert len(dup_entries) == 1
    assert dup_entries[0]["insight"] == "new"
