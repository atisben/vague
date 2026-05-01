"""Tests for observations commands."""

import json
import pytest
from typer.testing import CliRunner

from vague.sdk.cli import sdk_app

runner = CliRunner()


def _obs_json(**kwargs):
    defaults = {
        "skill": "ship",
        "type": "improvement",
        "issue": "Test issue",
        "suggestion": "Test suggestion",
        "principle": "Test principle",
        "source_skill": "ship",
    }
    defaults.update(kwargs)
    return json.dumps(defaults)


def test_observations_log_and_list(vague_home):
    result = runner.invoke(sdk_app, ["observations-log", _obs_json()])
    assert result.exit_code == 0
    assert "OK" in result.output

    result = runner.invoke(sdk_app, ["observations-list"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0]["skill"] == "ship"
    assert data[0]["id"] == 1


def test_observations_auto_increments_id(vague_home):
    runner.invoke(sdk_app, ["observations-log", _obs_json(skill="ship")])
    runner.invoke(sdk_app, ["observations-log", _obs_json(skill="review")])

    result = runner.invoke(sdk_app, ["observations-list"])
    data = json.loads(result.output)
    assert len(data) == 2
    assert data[0]["id"] == 1
    assert data[1]["id"] == 2


def test_observations_list_status_filter(vague_home):
    runner.invoke(sdk_app, ["observations-log", _obs_json(skill="ship")])
    runner.invoke(sdk_app, ["observations-log", _obs_json(skill="review")])

    # Mark first as actioned
    result = runner.invoke(sdk_app, ["observations-update", "1", "actioned"])
    assert result.exit_code == 0

    result = runner.invoke(sdk_app, ["observations-list", "--status", "open"])
    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0]["skill"] == "review"


def test_observations_update_not_found(vague_home):
    runner.invoke(sdk_app, ["observations-log", _obs_json()])
    result = runner.invoke(sdk_app, ["observations-update", "99", "actioned"])
    assert result.exit_code == 1


def test_observations_update_invalid_status(vague_home):
    runner.invoke(sdk_app, ["observations-log", _obs_json()])
    result = runner.invoke(sdk_app, ["observations-update", "1", "invalid"])
    assert result.exit_code == 1


def test_observations_log_sets_timestamp(vague_home):
    result = runner.invoke(sdk_app, ["observations-log", _obs_json()])
    assert result.exit_code == 0

    result = runner.invoke(sdk_app, ["observations-list"])
    data = json.loads(result.output)
    assert "ts" in data[0]
    assert data[0]["ts"] is not None
