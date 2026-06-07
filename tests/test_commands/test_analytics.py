"""Tests for analytics commands."""

import json

from typer.testing import CliRunner

from vague.sdk.cli import sdk_app

runner = CliRunner()


def test_analytics_log_and_show(vague_home):
    entry = json.dumps({
        "skill": "dev-ship",
        "ts": "2024-01-01T00:00:00+00:00",
        "repo": "owner-repo",
    })
    result = runner.invoke(sdk_app, ["analytics-log", entry])
    assert result.exit_code == 0
    assert "OK" in result.output


def test_analytics_show_json(vague_home):
    entry = json.dumps({
        "skill": "dev-review",
        "ts": "2024-01-01T00:00:00+00:00",
        "repo": "owner-repo",
    })
    runner.invoke(sdk_app, ["analytics-log", entry])
    result = runner.invoke(sdk_app, ["analytics-show", "all", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
